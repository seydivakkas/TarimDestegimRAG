"""Offline document-first retrieval: original PDF/HTML plus unreviewed OCR drafts.

This engine answers by retrieving and quoting actual indexed source text. It
never uses hard-coded tariff/FAQ answers or invented paragraphs.  It is a
document exploration tool, not a legal-approval/payment decision engine.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from rank_bm25 import BM25Plus

from tarim_destek_rag.retrieval.bm25 import tokenize_turkish

_SHA = re.compile(r"^[0-9a-f]{64}$")
_ARTICLE = re.compile(r"^(GEÇİCİ\s+)?MADDE\s+(\d+)\b", re.IGNORECASE)
_ALLOWED = {"resmigazete.gov.tr", "www.resmigazete.gov.tr",
            "www.tarimorman.gov.tr", "tarimorman.gov.tr"}
STOP = {"hangi", "nedir", "nelerdir", "nasıl", "bana", "anlat", "bilgi",
        "ver", "var", "mi", "mı", "mu", "mü", "ile", "için", "bir", "bu",
        "hangi", "ilgili", "belgede", "sayfada", "göre", "hakkında",
        "belgeler", "belge", "metin", "ne", "kaç", "ve", "veya"}
MAX_ORIGINAL_BYTES = 100_000_000
MAX_PASSAGES = 20000


@dataclass(frozen=True)
class SourcePassage:
    chunk_id: str
    source_id: str
    title: str
    document_sha256: str
    format: str
    page_number: int | None
    section: str
    text: str
    url: str
    extraction_method: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "title": self.title,
            "source_sha256": self.document_sha256,
            "format": self.format,
            "page_number": self.page_number,
            "section": self.section,
            "text": self.text,
            "url": self.url,
            "extraction_method": self.extraction_method,
            "review_status": "MACHINE_EXTRACTED_UNREVIEWED",
        }


def _windows(text: str, *, maximum: int = 950) -> list[str]:
    """Keep a little context across paragraphs without inventing sentences."""
    blocks = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
    if not blocks:
        blocks = [text.strip()] if text.strip() else []
    result: list[str] = []
    for block in blocks:
        # Original text is not rewritten, only split on existing whitespace.
        words = block.split()
        for begin in range(0, len(words), 115):
            part = " ".join(words[begin:begin + 135])
            if len(part) <= maximum:
                if part:
                    result.append(part)
            else:
                for start in range(0, len(part), maximum):
                    fragment = part[start:start + maximum].strip()
                    if fragment:
                        result.append(fragment)
    return result


def _passage(
    source: dict[str, Any], text: str, *, section: str,
    page: int | None, extraction: str, ordinal: int,
) -> SourcePassage:
    digest = source["original_sha256"]
    locator = f"pdf:{page}" if page is not None else f"html:{section}"
    chunk_id = hashlib.sha256(
        f"{digest}:{locator}:{ordinal}:{text}".encode("utf-8")
    ).hexdigest()[:24]
    if source.get("role") == "USER_DOCUMENT":
        url = (
            f"/documents/view/{digest}/page/{page}"
            if page is not None else f"/documents/view/{digest}/text"
        )
    else:
        url = source["url"] + (f"#page={page}" if page else "")
    return SourcePassage(
        chunk_id=chunk_id, source_id=source["id"],
        title=str(source.get("expected_legal_number") or
                  source.get("expected_annex_reference") or source["id"]),
        document_sha256=digest, format=source["format"],
        page_number=page, section=section,
        text=text, url=url, extraction_method=extraction,
    )


def _read_original(root: Path, source: dict[str, Any]) -> bytes:
    fmt = source.get("format")
    digest = source.get("original_sha256")
    url = source.get("url")
    if fmt not in ("pdf", "html") or not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError("Document is not pinned in the original manifest")
    if not isinstance(url, str):
        raise ValueError("Missing original source URL")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in _ALLOWED
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443)):
        raise ValueError("Unexpected source URL")
    path = root / "originals" / f"{digest}.{fmt}"
    raw = path.read_bytes()
    if (not raw or len(raw) > MAX_ORIGINAL_BYTES
            or type(source.get("original_bytes")) is not int
            or len(raw) != source["original_bytes"]
            or hashlib.sha256(raw).hexdigest() != digest):
        raise ValueError("Original document bytes differ from pinned source")
    return raw


def _pdf_passages(
    source: dict[str, Any], raw: bytes,
    index_dir: Path,
) -> tuple[list[SourcePassage], int, int]:
    import pymupdf

    chunks: list[SourcePassage] = []
    missing_ocr = 0
    image_pages = 0
    cached: dict[str, Any] = {}
    cache_file = index_dir / f"verified_ocr_{source['original_sha256']}.json"
    if cache_file.is_file() and cache_file.stat().st_size <= 30_000_000:
        try:
            parsed = json.loads(cache_file.read_text(encoding="utf-8"))
            with pymupdf.open(stream=raw, filetype="pdf") as doc:
                count = len(doc)
            pages = parsed.get("pages", [])
            if (
                parsed.get("schema_version") == 1
                and parsed.get("document_id") == source["id"]
                and parsed.get("original_sha256") == source["original_sha256"]
                and parsed.get("original_url") == source["url"]
                and parsed.get("original_page_count") == count
                and parsed.get("indexed_page_count") == count
                and isinstance(pages, list) and len(pages) == count
                and sorted(
                    p.get("page_number") for p in pages if isinstance(p, dict)
                ) == list(range(1, count + 1))
            ):
                cached = {str(p["page_number"]): p for p in pages}
        except (OSError, ValueError, KeyError, TypeError):
            cached = {}

    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        for index, pdf_page in enumerate(doc, start=1):
            native_text = pdf_page.get_text("text", sort=True).strip()
            method = "PDF_NATIVE_TEXT"
            text = native_text
            if not text:
                image_pages += 1
                entry = cached.get(str(index))
                if (entry and entry.get("source_sha256") == source["original_sha256"]
                        and entry.get("method") == "OCR_UNREVIEWED"
                        and isinstance(entry.get("text"), str)):
                    text = entry["text"].strip()
                    method = "OCR_DRAFT"
                if not text:
                    missing_ocr += 1
                    continue
            section = f"PDF sayfa {index}"
            for number, part in enumerate(_windows(text)):
                chunks.append(_passage(
                    source, part, section=section,
                    page=index, extraction=method, ordinal=number,
                ))
            # Born-digital table cells are native original PDF content. Keep
            # exact extracted strings in row/column order and the true page.
            # For image-only raster tables, rely on OCR_DRAFT snippets instead
            # of inventing headers, amounts or unseen cell relationships.
            if native_text:
                try:
                    tables = pdf_page.find_tables().tables
                    for table_no, table in enumerate(tables[:35], start=1):
                        extracted = table.extract()
                        if not extracted:
                            continue
                        columns = [str(v or "") for v in extracted[0]]
                        table_lines = [
                            "Sütunlar: " + " | ".join(columns)
                        ]
                        for row_no, row in enumerate(extracted[1:151], 1):
                            if not isinstance(row, list):
                                continue
                            table_lines.append(
                                f"Satır {row_no}: " +
                                " | ".join(str(v or "") for v in row)
                            )
                        for part_no, part in enumerate(
                            _windows("\n".join(table_lines), maximum=950)
                        ):
                            chunks.append(_passage(
                                source, part,
                                section=f"PDF sayfa {index} · Tablo {table_no}",
                                page=index, extraction="PDF_NATIVE_TABLE",
                                ordinal=10000 + table_no*200 + part_no,
                            ))
                except (AttributeError, ValueError, TypeError, RuntimeError):
                    # If the layout engine cannot extract actual cells,
                    # no fabricated table is added to the RAG index.
                    pass
    return chunks, image_pages, missing_ocr


def _html_passages(
    source: dict[str, Any], raw: bytes,
) -> list[SourcePassage]:
    # Resmi Gazete archive HTML sources in manifest are CP1254. Use the
    # original bytes, do NOT replace them with a synthesized PDF.
    decoded = (
        raw.decode("utf-8", errors="replace")
        if source.get("role") == "USER_DOCUMENT"
        else raw.decode("cp1254", errors="replace")
    )
    soup = BeautifulSoup(decoded, "html.parser")
    for tag in soup(["style", "script", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    section = "BELGE GENELİ"
    groups: list[tuple[str, list[str]]] = []
    current: list[str] = []
    for line in lines:
        match = _ARTICLE.match(line)
        if match:
            if current:
                groups.append((section, current))
            section = ("GEÇİCİ MADDE " if match.group(1) else "MADDE ") + match.group(2)
            current = []
        current.append(line)
    if current:
        groups.append((section, current))
    chunks: list[SourcePassage] = []
    for section, content in groups:
        for part in _windows("\n".join(content)):
            chunks.append(_passage(
                source, part, section=section, page=None,
                extraction="HTML_NATIVE_TEXT", ordinal=len(chunks),
            ))
    return chunks


class OriginalDocumentRAG:
    """Search only SHA-matching originals; optional local-only dense ranking."""

    def __init__(
        self, *, archive_root: Path | None = None,
        manifest_path: Path | None = None,
        ocr_index_dir: Path | None = None,
    ) -> None:
        self.archive_root = archive_root or Path(os.getenv(
            "TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
        self.manifest_path = manifest_path or Path(os.getenv(
            "TARIM_RAG_ORIGINAL_SOURCE_MANIFEST",
            "configs/p0_10_3_original_source_manifest.json"))
        self.ocr_index_dir = ocr_index_dir or Path(os.getenv(
            "TARIM_RAG_OCR_INDEX_DIR", "data/indexes"))
        self.user_library_root = Path(os.getenv(
            "TARIM_RAG_USER_DOC_DIR", "data/user_documents"))
        self.passages: list[SourcePassage] = []
        self.missing_sources: list[str] = []
        self.image_only_pages: int = 0
        self.pages_without_ocr: int = 0
        self._bm25: BM25Plus | None = None
        self._tokens: list[list[str]] = []
        self._dense: Any = None
        self._dense_vectors: Any = None

    def _add_discovered_annual_pdf_passages(self, seen_ids: set[str]) -> None:
        """Add only verified original PDF pages from annual scan to RAG.

        These are DISCOVERED_UNREVIEWED publications, not curated year-effective
        rule sources. Every OCR result is labelled unreviewed and points to a
        true original PDF page. Canonical source approval remains separate.
        """
        file = self.archive_root / "annual_research" / "catalog.json"
        if not file.is_file() or file.stat().st_size > 10_000_000:
            return
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if data.get("schema_version") != 1:
                return
            rows = data.get("documents", [])
            if not isinstance(rows, list) or len(rows) > 1000:
                return
        except (OSError, ValueError, TypeError):
            return
        for row in rows:
            try:
                from tarim_destek_rag.updates.annual_pdf_pipeline import (
                    _verify_doc,
                )
                sha = row["sha256"]
                key = "RG_DISCOVERED_" + sha[:16].upper()
                if key in seen_ids:
                    continue
                raw = _verify_doc(self.archive_root, row)
                source = {
                    "id": key,
                    "role": "DISCOVERED_OFFICIAL_UNREVIEWED",
                    "format": "pdf",
                    "url": row["source_url"],
                    "original_sha256": sha,
                    "original_bytes": len(raw),
                    "expected_legal_number": row.get("source_title") or key,
                }
                # Recheck original bytes via the existing RAG manifest reader.
                _read_original(self.archive_root, source)
                index = self.archive_root / "annual_research" / (sha + ".json")
                if not index.is_file() or index.stat().st_size > 30_000_000:
                    raise ValueError("Oversized/missing annually discovered index")
                draft = json.loads(index.read_text(encoding="utf-8"))
                page_rows = draft.get("pages", [])
                if (draft.get("schema_version") != 1
                        or draft.get("source_sha256") != sha
                        or draft.get("source_url") != row["source_url"]
                        or draft.get("original_bytes") != len(raw)
                        or not isinstance(page_rows, list)
                        or len(page_rows) > 120):
                    raise ValueError("Untrusted annual page index")
                from pymupdf import open as open_pdf
                with open_pdf(stream=raw, filetype="pdf") as pdf:
                    count = len(pdf)
                    if draft.get("original_page_count") != count:
                        raise ValueError("Original page count mismatched")
                    if any(type(item.get("page")) is not int
                           or not 1 <= item["page"] <= count
                           or item.get("source_sha256") != sha
                           for item in page_rows):
                        raise ValueError("Unverified annual page location")
                new: list[SourcePassage] = []
                for item in page_rows:
                    text = item.get("text")
                    if not isinstance(text, str) or not text.strip():
                        continue
                    method = item.get("method")
                    if method not in (
                        "PDF_NATIVE_TEXT_UNREVIEWED",
                        "TESSERACT_OCR_180DPI_UNREVIEWED",
                    ):
                        continue
                    for ordinal, fragment in enumerate(_windows(text)):
                        new.append(_passage(
                            source, fragment, section=f"PDF sayfa {item['page']}",
                            page=item["page"],
                            extraction=("OCR_DRAFT" if method.startswith("TESSERACT")
                                        else "PDF_NATIVE_TEXT"),
                            ordinal=ordinal,
                        ))
                if len(self.passages) + len(new) > MAX_PASSAGES:
                    self.missing_sources.append(key + ":PASSAGE_LIMIT_HOLD")
                    continue
                self.passages.extend(new)
                seen_ids.add(key)
                if not draft.get("complete_page_coverage"):
                    self.missing_sources.append(key + ":PARTIAL_PDF_INDEX_HOLD")
            except (OSError, ValueError, KeyError, RuntimeError,
                    ImportError, TypeError, AttributeError):
                self.missing_sources.append(
                    "RG_DISCOVERED_" + str(row.get("sha256", ""))[:16] + ":HOLD"
                )


    def build(self) -> dict[str, Any]:
        self.passages = []
        self.missing_sources = []
        self.image_only_pages = 0
        self.pages_without_ocr = 0
        self._bm25 = None
        self._dense = None
        self._dense_vectors = None
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        ids: set[str] = set()
        for source in manifest.get("sources", []):
            key = source.get("id")
            if not isinstance(key, str) or key in ids:
                raise ValueError("Untrusted duplicate/missing source identity")
            ids.add(key)
            try:
                raw = _read_original(self.archive_root, source)
                if source["format"] == "pdf":
                    chunks, image_pages, missing_ocr = _pdf_passages(
                        source, raw, self.ocr_index_dir)
                    self.image_only_pages += image_pages
                    self.pages_without_ocr += missing_ocr
                else:
                    chunks = _html_passages(source, raw)
                self.passages.extend(chunks)
            except (OSError, ValueError, TypeError, ImportError, RuntimeError, KeyError):
                self.missing_sources.append(key)
        # Optional annual Gazette updates are research-only source candidates.
        # They do NOT become effective rules or legal/year-approved citations.
        self._add_discovered_annual_pdf_passages(ids)

        # User-uploaded files have their OWN provenance label, not an
        # official Gazette source. Their original bytes are still SHA-pinned.
        from tarim_destek_rag.retrieval.user_documents import (
            library_entries,
            load_user_original,
        )

        for item in library_entries(self.user_library_root):
            digest = item.get("sha256")
            if not isinstance(digest, str) or not _SHA.fullmatch(digest):
                continue
            try:
                meta, raw = load_user_original(
                    digest, root=self.user_library_root)
                source = {
                    "id": meta["id"],
                    "role": "USER_DOCUMENT",
                    "original_sha256": digest,
                    "original_bytes": len(raw),
                    "format": meta["format"],
                    "url": f"/documents/view/{digest}",
                    "expected_legal_number": str(meta["filename"]),
                }
                if source["format"] == "pdf":
                    chunks, image_pages, missing_ocr = _pdf_passages(
                        source, raw, self.ocr_index_dir,
                    )
                    self.image_only_pages += image_pages
                    self.pages_without_ocr += missing_ocr
                elif source["format"] == "html":
                    chunks = _html_passages(source, raw)
                else:
                    text = raw.decode("utf-8", errors="replace")
                    chunks = [
                        _passage(source, textpart, section="TXT METNİ",
                                 page=None, extraction="TXT_NATIVE_TEXT",
                                 ordinal=i)
                        for i, textpart in enumerate(_windows(text))
                    ]
                self.passages.extend(chunks)
            except (OSError, ValueError, KeyError, RuntimeError, ImportError):
                self.missing_sources.append(str(item.get("id", "USER_UNKNOWN")))

        if len(self.passages) > MAX_PASSAGES:
            raise ValueError("Source corpus exceeds local safety budget")
        self._tokens = [
            tokenize_turkish(f"{p.title} {p.section} {p.text}")
            for p in self.passages
        ]
        if self._tokens:
            self._bm25 = BM25Plus(self._tokens)
        # An optional *locally installed* sentence embedding model. Never
        # fetch a remote model or API silently, including first-run downloads.
        local_model = os.getenv("TARIM_RAG_LOCAL_EMBEDDING_DIR", "")
        if local_model and Path(local_model).is_dir() and self.passages:
            try:
                import numpy as np
                from sentence_transformers import SentenceTransformer

                self._dense = SentenceTransformer(
                    str(Path(local_model).resolve()), local_files_only=True)
                self._dense_vectors = self._dense.encode(
                    [p.text for p in self.passages],
                    convert_to_numpy=True, normalize_embeddings=True,
                    batch_size=16, show_progress_bar=False,
                ).astype(np.float32)
            except (ImportError, OSError, ValueError, RuntimeError):
                self._dense = None
                self._dense_vectors = None
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "source_count": len({p.source_id for p in self.passages}),
            "native_table_passage_count": sum(
                p.extraction_method == "PDF_NATIVE_TABLE" for p in self.passages
            ),
            "indexed_documents": [
                {"source_id": p.source_id, "title": p.title, "format": p.format}
                for p in {p.source_id: p for p in self.passages}.values()
            ],
            "passage_count": len(self.passages),
            "missing_source_ids": self.missing_sources,
            "image_only_pdf_pages": self.image_only_pages,
            "pdf_pages_without_ocr": self.pages_without_ocr,
            "search_mode": (
                "BM25_PLUS_LOCAL_DENSE_RRF"
                if self._dense_vectors is not None else "BM25_ONLY_OFFLINE"
            ),
            "document_analysis_only": True,
        }

    def search(
        self, query: str, *, top_k: int = 5,
        source_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not 1 <= top_k <= 10:
            return []
        tokens = [t for t in tokenize_turkish(query) if t not in STOP]
        if not tokens or self._bm25 is None:
            return []
        distinct = set(tokens)
        scores = self._bm25.get_scores(tokens)
        lexical_ranks = sorted(
            (
                (i, float(score))
                for i, score in enumerate(scores)
                if (not source_id or self.passages[i].source_id == source_id)
                and set(self._tokens[i]).intersection(distinct)
            ),
            key=lambda x: x[1], reverse=True,
        )[:max(20, top_k*5)]
        rrf: dict[int, float] = {}
        for rank, (idx, _) in enumerate(lexical_ranks, 1):
            rrf[idx] = rrf.get(idx, 0) + 0.75 / (60 + rank)
        if self._dense is not None and self._dense_vectors is not None:
            import numpy as np

            embedding = self._dense.encode(
                [query], convert_to_numpy=True, normalize_embeddings=True,
            )[0].astype(np.float32)
            similarities = self._dense_vectors @ embedding
            for rank, i in enumerate(np.argsort(-similarities)[:80], start=1):
                idx = int(i)
                if source_id and self.passages[idx].source_id != source_id:
                    continue
                if not set(self._tokens[idx]).intersection(distinct):
                    continue
                rrf[idx] = rrf.get(idx, 0) + .25 / (60 + rank)
        ranked = sorted(rrf, key=lambda idx: (-rrf[idx], idx))
        results: list[dict[str, Any]] = []
        for idx in ranked[:top_k]:
            item = self.passages[idx].as_dict()
            item["retrieval_score"] = round(rrf[idx], 7)
            results.append(item)
        return results

    def answer(
        self, question: str, *, top_k: int = 4,
        source_id: str | None = None,
    ) -> dict[str, Any]:
        hits = self.search(question, top_k=top_k, source_id=source_id)
        if not hits:
            return {
                "question": question,
                "answer": (
                    "İndekslenen özgün belgelerde bu soruyu destekleyen metin "
                    "bulunamadı. Taranmış sayfaların OCR'si eksik olabilir; "
                    "kaynak belgeyi ve sayfayı doğrudan inceleyin."
                ),
                "citations": [],
                "status": "NO_GROUNDED_ANSWER",
                "corpus_status": self.status(),
            }
        sentences = []
        for i, hit in enumerate(hits, start=1):
            # Extractive RAG: the body is always drawn from stored original text,
            # never from a disconnected hard-coded tariff or generic template.
            lines = re.split(r"(?<=[.!?])\s+|\n+", hit["text"])
            needle = set(tokenize_turkish(question)) - STOP
            ranked_lines = sorted(
                (s.strip() for s in lines if len(s.strip()) >= 20),
                key=lambda s: -len(set(tokenize_turkish(s)).intersection(needle)),
            )
            quote = (ranked_lines[0] if ranked_lines else hit["text"][:420])[:480]
            suffix = (
                f"sayfa {hit['page_number']}"
                if hit["page_number"] is not None else hit["section"]
            )
            sentences.append(f"[{i}] {hit['title']} ({suffix}): {quote}")
        return {
            "question": question,
            "answer": (
                "Belgelerde bulunan ilgili bölümler (doğrudan metin çıkarımı):\n\n"
                + "\n\n".join(sentences)
                + "\n\nNot: Bunlar belge içeriği ve OCR ön okumalarıdır; "
                  "OCR veya belge metnindeki bilgileri bağımsız kontrol edebilirsiniz."
            ),
            "citations": hits,
            "status": "SOURCE_PASSAGES_FOUND",
            "corpus_status": self.status(),
        }


_DOCUMENT_RAG: OriginalDocumentRAG | None = None


def get_document_rag(*, refresh: bool = False) -> OriginalDocumentRAG:
    """Lazy cache; rerun explicitly after installing/refreshing original PDFs."""
    global _DOCUMENT_RAG
    if _DOCUMENT_RAG is None or refresh:
        engine = OriginalDocumentRAG()
        engine.build()
        _DOCUMENT_RAG = engine
    return _DOCUMENT_RAG
