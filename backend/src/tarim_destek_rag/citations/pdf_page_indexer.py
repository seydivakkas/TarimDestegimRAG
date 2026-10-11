"""SHA-pinned original PDF screenshot explorer; never create a Gazette PDF."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

HOLD_HTML = (
    '<section style="padding:20px;border-left:5px solid #d97706;'
    'background:#fffbeb"><strong>HOLD — Özgün kanıt bulunamadı.</strong>'
    '<p>SHA-256 ile doğrulanmış gerçek belge/sayfa yok; sentetik PDF, '
    'tahmini hüküm, yanlış sayfa veya sahte OCR gösterilmez.</p></section>'
)
_GLOBAL_INDEXER: OfficialPdfIndexer | None = None


def normalize_tr(text: str) -> str:
    t = (text or "").casefold().replace("ı", "i").replace("i̇", "i")
    for a, b in (("ğ", "g"), ("ü", "u"), ("ş", "s"), ("ö", "o"), ("ç", "c")):
        t = t.replace(a, b)
    return " ".join(t.split())


@dataclass
class PageTableData:
    table_id: str
    bbox: tuple[float, float, float, float]
    headers: list[str]
    rows: list[list[str]]
    markdown: str = ""
    row_count: int = 0
    col_count: int = 0


@dataclass
class PageGraphicsData:
    drawings_count: int = 0
    images_count: int = 0
    summary: str = ""
    has_table_borders: bool = False
    has_official_seal: bool = False


@dataclass
class OfficialGazettePageRecord:
    doc_id: str
    doc_title: str
    page_number: int
    total_pages: int
    gazette_issue: str
    gazette_date: str
    official_url: str
    raw_text: str = ""
    highlighted_html: str = ""
    articles_contained: list[str] = field(default_factory=list)
    tables: list[PageTableData] = field(default_factory=list)
    graphics: PageGraphicsData = field(default_factory=PageGraphicsData)
    image_path: str | None = None
    image_base64: str | None = None
    keywords: list[str] = field(default_factory=list)
    source_sha256: str = ""
    text_status: str = "IMAGE_ONLY_OCR_PENDING"


class OfficialPdfIndexer:
    """No historical JSON cache can be trusted without rechecking original bytes."""

    def __init__(
        self, index_path: Path | str | None = None,
        image_dir: Path | str | None = None, *,
        archive_root: Path | str | None = None,
        manifest_path: Path | str | None = None,
    ) -> None:
        self.index_path = Path(index_path or "data/indexes/gazette_page_index.json")
        self.image_dir = Path(image_dir or "data/indexes/page_previews")
        self.archive_root = Path(archive_root or os.getenv(
            "TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
        self.manifest_path = Path(manifest_path or os.getenv(
            "TARIM_RAG_ORIGINAL_SOURCE_MANIFEST",
            "configs/p0_10_3_original_source_manifest.json"))
        self._records: dict[str, list[OfficialGazettePageRecord]] = {}

    def _source(self, doc_id: str) -> dict[str, Any]:
        sources = json.loads(self.manifest_path.read_text(encoding="utf-8"))["sources"]
        selected = [s for s in sources
                    if s.get("id") == doc_id and s.get("format") == "pdf"]
        if len(selected) != 1:
            raise ValueError("Missing or ambiguous original PDF source")
        item = selected[0]
        url, digest = item.get("url"), item.get("original_sha256")
        if (not isinstance(digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
                or not isinstance(url, str)
                or not url.startswith("https://")
                or url.split("/")[2] not in (
                    "www.resmigazete.gov.tr", "resmigazete.gov.tr",
                    "www.tarimorman.gov.tr", "tarimorman.gov.tr")):
            raise ValueError("Unpinned or untrusted official source identity")
        return item

    def _verified_pdf(self, doc_id: str) -> tuple[dict[str, Any], bytes]:
        source = self._source(doc_id)
        digest = source["original_sha256"]
        raw = (self.archive_root / "originals" / (digest + ".pdf")).read_bytes()
        if (not raw or len(raw) > 100_000_000
                or (source.get("original_bytes") is not None
                    and len(raw) != source["original_bytes"])
                or hashlib.sha256(raw).hexdigest() != digest):
            raise ValueError("Original PDF digest/size mismatch")
        return source, raw

    def index_pdf(
        self, pdf_bytes: bytes, *, doc_id: str, doc_title: str,
        gazette_issue: str, gazette_date: str, official_url: str,
        save_rendered_images: bool = False, render_dpi: int = 144,
    ) -> list[OfficialGazettePageRecord]:
        import pymupdf

        item, original = self._verified_pdf(doc_id)
        if (pdf_bytes != original or official_url != item["url"]
                or save_rendered_images or not 72 <= render_dpi <= 250):
            raise ValueError("An unsigned/synthetic PDF cannot be official evidence")
        pages: list[OfficialGazettePageRecord] = []
        with pymupdf.open(stream=original, filetype="pdf") as doc:
            if not 1 <= len(doc) <= 1000:
                raise ValueError("Invalid original page count")
            for i, page in enumerate(doc):
                raw_text = page.get_text("text").strip()
                tables = []
                if raw_text:
                    try:
                        for num, table in enumerate(page.find_tables().tables, 1):
                            cells = table.extract()
                            if cells:
                                header = [str(v or "") for v in cells[0]]
                                rows = [[str(v or "") for v in row] for row in cells[1:]]
                                tables.append(PageTableData(
                                    table_id=f"{doc_id}:P{i+1}:T{num}",
                                    bbox=tuple(table.bbox), headers=header,
                                    rows=rows, row_count=len(rows),
                                    col_count=len(header),
                                ))
                    except (AttributeError, ValueError, TypeError):
                        pass
                pages.append(OfficialGazettePageRecord(
                    doc_id=doc_id, doc_title=doc_title, page_number=i+1,
                    total_pages=len(doc), gazette_issue=gazette_issue,
                    gazette_date=gazette_date,
                    official_url=f"{official_url}#page={i+1}",
                    raw_text=raw_text, tables=tables,
                    articles_contained=sorted(set(re.findall(
                        r"(?:GEÇİCİ\s+)?MADDE\s+\d+", raw_text, re.I))),
                    source_sha256=item["original_sha256"],
                    graphics=PageGraphicsData(
                        drawings_count=len(page.get_drawings()),
                        images_count=len(page.get_images()),
                        summary="Görsel yerleşim bilgisi; resmî mühür doğrulaması değildir.",
                    ),
                    text_status=("PDF_TEXT_LAYER_UNREVIEWED" if raw_text
                                 else "IMAGE_ONLY_OCR_PENDING"),
                ))
        self._records[doc_id] = pages
        return pages

    def seed_default_gazette_documents(self) -> None:
        """Compatibility entry point, never generates or writes PDF files."""
        self.load_verified_originals()

    def load_verified_originals(self) -> None:
        try:
            sources = json.loads(self.manifest_path.read_text(encoding="utf-8"))["sources"]
        except (OSError, ValueError, TypeError, KeyError):
            return
        for item in sources:
            doc_id = item.get("id")
            if item.get("format") != "pdf" or not isinstance(doc_id, str):
                continue
            try:
                trusted, data = self._verified_pdf(doc_id)
                self.index_pdf(data, doc_id=doc_id, doc_title=doc_id,
                               gazette_issue=str(trusted.get("gazette_issue") or ""),
                               gazette_date=str(trusted.get("gazette_date") or ""),
                               official_url=trusted["url"])
            except (OSError, ValueError, TypeError, RuntimeError, KeyError):
                continue  # HOLD: source absent or does not match source manifest.

    def get_all_pages(self) -> list[OfficialGazettePageRecord]:
        return [page for pages in self._records.values() for page in pages]

    def get_page(self, doc_id: str, number: int) -> OfficialGazettePageRecord | None:
        if type(number) is not int or number < 1:
            return None
        return next((p for p in self._records.get(doc_id, [])
                     if p.page_number == number), None)

    def search_pages(self, query: str, *, top_k: int = 3) -> list[OfficialGazettePageRecord]:
        needle = normalize_tr(query)
        if len(needle) < 2 or not 1 <= top_k <= 20:
            return []
        ranked = [(normalize_tr(p.raw_text).count(needle), p)
                  for p in self.get_all_pages() if p.raw_text]
        return [page for count, page in sorted(ranked, key=lambda x: -x[0])
                if count][:top_k]

    def get_article_page(self, key: str) -> OfficialGazettePageRecord | None:
        return next(iter(self.search_pages(key, top_k=1)), None)

    def screenshot(
        self, record: OfficialGazettePageRecord, *,
        query: str = "", dpi: int = 175,
    ) -> tuple[bytes, int, str]:
        """Render the selected page from SHA-verified bytes on every view."""
        import pymupdf

        if not 120 <= dpi <= 250:
            raise ValueError("Invalid screenshot DPI")
        source, raw = self._verified_pdf(record.doc_id)
        if (record.source_sha256 != source["original_sha256"]
                or record.official_url !=
                    f"{source['url']}#page={record.page_number}"):
            raise ValueError("Untrusted cached page or wrong original URL")
        with pymupdf.open(stream=raw, filetype="pdf") as doc:
            if (type(record.page_number) is not int
                    or not 1 <= record.page_number <= len(doc)
                    or record.total_pages != len(doc)):
                raise ValueError("Wrong PDF page")
            page = doc[record.page_number-1]
            hits = []
            if (query and record.text_status == "PDF_TEXT_LAYER_UNREVIEWED"
                    and len(query) <= 120):
                hits = page.search_for(query)
                for rect in hits[:12]:
                    mark = page.add_highlight_annot(rect)
                    mark.set_colors(stroke=(1, 0.82, 0))
                    mark.update(opacity=0.38)
            image = page.get_pixmap(dpi=dpi, alpha=False).tobytes("png")
        return image, len(hits), source["original_sha256"]

    def ocr_page(self, record: OfficialGazettePageRecord) -> tuple[str, str]:
        """Actual opt-in local OCR, never an invented transcribed legal quotation."""
        if not shutil.which("tesseract"):
            return "", "OCR_NOT_INSTALLED"
        try:
            image, _, _ = self.screenshot(record, dpi=180)
            run = subprocess.run(
                ["tesseract", "stdin", "stdout", "-l", "tur+eng"],
                input=image, capture_output=True, timeout=45, check=False,
            )
            if run.returncode != 0:
                return "", "OCR_FAILED"
            return run.stdout.decode("utf-8", errors="replace").strip(), "OCR_UNREVIEWED"
        except (ValueError, OSError, subprocess.TimeoutExpired):
            return "", "OCR_FAILED"


def get_global_pdf_indexer() -> OfficialPdfIndexer:
    global _GLOBAL_INDEXER
    if _GLOBAL_INDEXER is None:
        _GLOBAL_INDEXER = OfficialPdfIndexer()
        _GLOBAL_INDEXER.load_verified_originals()
    return _GLOBAL_INDEXER


def get_page_dropdown_choices() -> list[tuple[str, str]]:
    return [
        (f"{p.doc_id} · Gerçek sayfa {p.page_number}/{p.total_pages}",
         f"{p.doc_id}:{p.page_number}")
        for p in get_global_pdf_indexer().get_all_pages()
    ]


def render_page_evidence_card(
    record: OfficialGazettePageRecord, query: str = "",
    *, indexer: OfficialPdfIndexer | None = None,
) -> str:
    """Full-width screenshot from original; no fabricated paragraph or table."""
    idx = indexer or get_global_pdf_indexer()
    try:
        picture, hits, digest = idx.screenshot(record, query=query)
    except (OSError, ValueError, RuntimeError, KeyError):
        return HOLD_HTML
    img = base64.b64encode(picture).decode("ascii")
    status = ("PDF metin katmanı: hukukî inceleme bekliyor"
              if record.raw_text else
              "Taranmış sayfa: OCR/pasaj eşleşmesi henüz onaylanmadı")
    highlights = (f"{hits} birebir PDF metin eşleşmesi sarı işaretlendi"
                  if hits else "Kesin pasaj bulunamadı; sarı vurgu üretilmedi")
    return (
        '<section style="padding:16px;border:1px solid #cbd5e1;'
        'border-radius:12px;background:white;max-width:1100px">'
        f'<h3>Özgün PDF sayfa ekran görüntüsü — {escape(record.doc_title)}</h3>'
        f'<p>Sayfa {record.page_number}/{record.total_pages} · {escape(status)}</p>'
        f'<img alt="Gerçek PDF sayfa {record.page_number}" '
        f'src="data:image/png;base64,{img}" '
        'style="width:100%;height:auto;border:1px solid #94a3b8;'
        'box-shadow:0 6px 20px #0002" />'
        f'<p><a href="{escape(record.official_url, quote=True)}" '
        'target="_blank" rel="noopener noreferrer">'
        f'Özgün resmî PDF dosyasındaki sayfa {record.page_number} ↗</a></p>'
        f'<p>Kaynak SHA-256: <code>{escape(digest)}</code></p>'
        f'<p>{escape(highlights)}. OCR ve metin çıkarımı tek başına '
        'hak ediş veya hukukî uygunluk onayı değildir.</p></section>'
    )


def render_evidence_by_key(choice_key: str, search_query: str = "") -> str:
    idx = get_global_pdf_indexer()
    if search_query.strip():
        matches = idx.search_pages(search_query, top_k=1)
        if matches:
            return render_page_evidence_card(matches[0], search_query, indexer=idx)
        # OCR is unreviewed: it may suggest a REAL page image, never prove
        # a passage or claim. No yellow annotation for OCR-only candidates.
        from tarim_destek_rag.citations.verified_ocr_index import search_ocr_candidates

        candidates = search_ocr_candidates(idx, search_query, index_dir=Path(
            os.getenv("TARIM_RAG_OCR_INDEX_DIR", "data/indexes")))
        if candidates:
            candidate = candidates[0]
            page = idx.get_page(candidate["document_id"], candidate["page_number"])
            if page is not None:
                return (
                    '<p style="background:#fffbeb;padding:12px">'
                    '<strong>HOLD — OCR arama adayı.</strong> Metnin bu sayfada '
                    'birebir bulunduğu hukukî olarak doğrulanmadı; aşağıdaki '
                    'özgün ekran görüntüsünü kendiniz kontrol edin.</p>'
                    + render_page_evidence_card(page, indexer=idx)
                )
        return HOLD_HTML
    if not choice_key or ":" not in choice_key:
        return HOLD_HTML
    doc_id, number = choice_key.rsplit(":", 1)
    if not number.isdigit():
        return HOLD_HTML
    found = idx.get_page(doc_id, int(number))
    return render_page_evidence_card(found, indexer=idx) if found else HOLD_HTML

def render_ocr_page_by_key(choice_key: str | None) -> str:
    """Opt-in local OCR of a selected verified original page; never auto-approve."""
    if not choice_key or ":" not in choice_key:
        return HOLD_HTML
    doc_id, raw_page = choice_key.rsplit(":", 1)
    if not raw_page.isdigit():
        return HOLD_HTML
    idx = get_global_pdf_indexer()
    page = idx.get_page(doc_id, int(raw_page))
    if page is None:
        return HOLD_HTML
    try:
        idx.screenshot(page)  # bytes + page verified before OCR/status output
        text, status = idx.ocr_page(page)
    except (OSError, ValueError, RuntimeError, KeyError):
        return HOLD_HTML
    if status != "OCR_UNREVIEWED" or not text:
        return (
            '<p style="border-left:4px solid #d97706;padding:12px">'
            'OCR kullanılamıyor veya Türkçe dil modeli yüklü değil. '
            'Görüntüden metin uydurulmadı; özgün sayfayı inceleyin. '
            f'Durum: {escape(status)}</p>'
        )
    return (
        '<section style="border:1px solid #f59e0b;padding:14px">'
        '<strong>OCR ÖN TASLAĞI — Hukukî alıntı/doğrulama değildir (HOLD)</strong>'
        '<p>Aşağıdaki karakterler seçilen özgün sayfanın yerel Tesseract '
        'çıktısıdır. Hatalı okunan tutar, hücre, grafik ve hükümler olabilir. '
        'Bağımsız insan incelemesi ve kaynak koordinatı zorunludur.</p>'
        f'<pre style="white-space:pre-wrap;overflow:auto">{escape(text[:16000])}</pre>'
        '</section>'
    )
