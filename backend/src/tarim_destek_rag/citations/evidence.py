"""Resmî kaynak dosyasından sayfa/pasaj eşleştirmeli kanıt doğrulaması.

Bir URL, başlık ya da özet metin tek başına kanıt değildir. Önce kontrollü
HTTPS kaynağından gerçek belge indirilir, hash ve metin sayfaları saklanır.
Doğrulama sırasında yalnız aynı belgedeki kelimesi kelimesine pasajlar kabul edilir.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urldefrag, urlsplit

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from tarim_destek_rag.models.source import ContentTypeEnum, SourceDefinition

MAX_DOCUMENT_BYTES = 12 * 1024 * 1024
OFFICIAL_DOMAINS = frozenset({"resmigazete.gov.tr", "tarimorman.gov.tr"})


class EvidenceError(ValueError):
    """Kanıt kaynağı güvenlik, biçim veya bütünlük hatası."""


def canonical_url(url: str) -> str:
    """URL fragment'ı belge kaynağının bir parçası değildir; sorgu ve yol korunur."""
    raw = urldefrag(str(url))[0]
    parsed = urlsplit(raw)
    # HTTPS alan adında "/" ile boş yol aynı kök kaynağı temsil eder.
    return parsed._replace(path=parsed.path or "/").geturl()


def require_official_https(url: str) -> None:
    p = urlsplit(canonical_url(url))
    host = (p.hostname or "").lower()
    official = any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443) or not official:
        raise EvidenceError("Kaynak HTTPS ve izinli resmî alan adı olmalıdır.")


def normalize_passage(text: str) -> str:
    """Türkçe harfleri koruyarak satır kaymalarını ve noktalama ayırıcılarını normalize eder."""
    text = unicodedata.normalize("NFKC", text).casefold().replace("\u0307", "")
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def extract_document_pages(content: bytes, content_type: ContentTypeEnum) -> tuple[str, ...]:
    if not content or len(content) > MAX_DOCUMENT_BYTES:
        raise EvidenceError("Boş veya boyut sınırını aşan belge.")
    if content_type == ContentTypeEnum.PDF:
        if not content.startswith(b"%PDF-"):
            raise EvidenceError("PDF imzası bulunamadı.")
        try:
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise EvidenceError("Şifreli PDF desteklenmiyor.")
            if len(reader.pages) > 500:
                raise EvidenceError("PDF sayfa sınırı aşıldı.")
            pages = tuple((page.extract_text() or "").strip() for page in reader.pages)
        except EvidenceError:
            raise
        except Exception as exc:
            raise EvidenceError("PDF metni çıkarılamadı.") from exc
    elif content_type == ContentTypeEnum.HTML:
        text = content.decode("utf-8-sig", errors="strict")
        soup = BeautifulSoup(text, "html.parser")
        for node in soup(["script", "style", "noscript"]):
            node.decompose()
        pages = (soup.get_text(separator=" ", strip=True),)
    else:
        raise EvidenceError("Yalnız PDF veya HTML kanıtları destekleniyor.")
    if not any(normalize_passage(page) for page in pages):
        raise EvidenceError("Belgede okunabilir metin yok; taranmış PDF için OCR gerekli.")
    return pages


@dataclass(frozen=True)
class EvidenceSnapshot:
    source_id: str
    source_url: str
    content_type: ContentTypeEnum
    sha256: str
    fetched_at: str
    pages: tuple[str, ...]


class EvidenceStore:
    """Snapshot'lar diskten doğrulanarak yüklenir; ağ çağrıları yalnız açık ingest ile olur."""

    def __init__(self, root: str | Path = "data/evidence") -> None:
        self.root = Path(root)
        self._snapshots: dict[str, EvidenceSnapshot] = {}

    def index_bytes(
        self, source: SourceDefinition, content: bytes, *,
        fetched_at: str | None = None, expected_sha256: str | None = None,
    ) -> EvidenceSnapshot:
        require_official_https(str(source.url))
        pages = extract_document_pages(content, source.content_type)
        digest = hashlib.sha256(content).hexdigest()
        if expected_sha256 and digest != expected_sha256.lower():
            raise EvidenceError("Belge SHA-256 beklenen hash ile uyuşmuyor.")
        snapshot = EvidenceSnapshot(
            source_id=source.id,
            source_url=canonical_url(str(source.url)),
            content_type=source.content_type,
            sha256=digest,
            fetched_at=fetched_at or datetime.now(UTC).isoformat(),
            pages=pages,
        )
        self._snapshots[source.id] = snapshot
        return snapshot

    def ingest_official(self, source: SourceDefinition, *, timeout: float = 20.0) -> EvidenceSnapshot:
        """Şeffaf HTTPS istek; otomatik yönlendirme ve harici URL kabul edilmez."""
        require_official_https(str(source.url))
        if not source.active:
            raise EvidenceError("Pasif kaynağın kanıtı indekslenemez.")
        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            with client.stream("GET", str(source.url), headers={"User-Agent": "TarimDestekRAG-Evidence/1.0"}) as resp:
                if resp.status_code != 200:
                    raise EvidenceError(f"Resmî kaynaktan HTTP {resp.status_code} alındı.")
                ct = resp.headers.get("content-type", "").lower()
                expected = "application/pdf" if source.content_type == ContentTypeEnum.PDF else "text/html"
                if expected not in ct:
                    raise EvidenceError(f"Beklenen içerik türü {expected}, gelen: {ct}")
                chunks: list[bytes] = []
                size = 0
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > MAX_DOCUMENT_BYTES:
                        raise EvidenceError("İndirilen belge boyut sınırını aşıyor.")
                    chunks.append(chunk)
                content = b"".join(chunks)
        snapshot = self.index_bytes(source, content)
        self.save_snapshot(snapshot, content)
        return snapshot

    def save_snapshot(self, snapshot: EvidenceSnapshot, content: bytes) -> None:
        """Hash üzerinde kilitlenmiş ham dosya + kaynak meta verisi kaydet."""
        digest = hashlib.sha256(content).hexdigest()
        if digest != snapshot.sha256:
            raise EvidenceError("Yazılacak belge ile hash eşleşmiyor.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", snapshot.source_id):
            raise EvidenceError("Güvensiz source_id.")
        suffix = ".pdf" if snapshot.content_type == ContentTypeEnum.PDF else ".html"
        folder = self.root / snapshot.source_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{digest}{suffix}").write_bytes(content)
        (folder / "active.json").write_text(json.dumps({
            "source_id": snapshot.source_id,
            "source_url": snapshot.source_url,
            "content_type": snapshot.content_type.value,
            "sha256": digest,
            "fetched_at": snapshot.fetched_at,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_snapshot(self, source: SourceDefinition) -> EvidenceSnapshot | None:
        """Snapshot dosyasını yeniden hash'leyerek doğrular; bozulma sessizce geçmez."""
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", source.id):
            return None
        index = self.root / source.id / "active.json"
        if not index.is_file():
            return None
        try:
            record = json.loads(index.read_text(encoding="utf-8"))
            digest = record["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                return None
            if (record["source_id"] != source.id
                or record["source_url"] != canonical_url(str(source.url))
                or record["content_type"] != source.content_type.value):
                return None
            suffix = ".pdf" if source.content_type == ContentTypeEnum.PDF else ".html"
            data = (index.parent / f"{digest}{suffix}").read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                return None
            return self.index_bytes(
                source, data, fetched_at=record["fetched_at"], expected_sha256=digest
            )
        except (OSError, ValueError, KeyError, TypeError, UnicodeError):
            return None

    def get(self, source_id: str) -> EvidenceSnapshot | None:
        return self._snapshots.get(source_id)

    def match(self, source: SourceDefinition, *, snippet: str, section: str = "") -> tuple[bool, int | None]:
        """Aynı sayfada hem bölüm başlığı hem alıntı metni tam eşleşmelidir."""
        snapshot = self.get(source.id)
        if snapshot is None or snapshot.source_url != canonical_url(str(source.url)):
            return False, None
        passage = normalize_passage(snippet)
        heading = normalize_passage(section)
        if len(passage) < 15 or "..." in snippet or not passage:
            return False, None
        for i, page in enumerate(snapshot.pages, start=1):
            normalized = normalize_passage(page)
            if passage in normalized and (not heading or heading in normalized):
                return True, i
        return False, None
