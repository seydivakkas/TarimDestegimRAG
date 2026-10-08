import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from tarim_destek_rag.config.settings import settings
from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.models.source import ContentTypeEnum, SourceDefinition


class ScraperClientError(Exception):
    """Scraper HTTP istemci genel hatası."""


class ScraperTimeoutError(ScraperClientError):
    """Zaman aşımı hatası."""


class InvalidMimeTypeError(ScraperClientError):
    """Desteklenmeyen veya uyumsuz MIME türü hatası."""


class ScraperClient:
    """Nezaketli (rate-limited) ve dayanıklı (retry'li) resmî kaynak HTTP istemcisi."""

    def __init__(
        self,
        user_agent: str = "TarimDestekRAG-Bot/1.0 (+https://github.com/seydivakkas)",
        timeout: float | None = None,
        max_retries: int | None = None,
        rate_limit_seconds: float | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout or settings.scraper_timeout_seconds
        self.max_retries = max_retries or settings.scraper_max_retries
        self.rate_limit_seconds = rate_limit_seconds or settings.scraper_rate_limit_seconds
        self._last_request_time: float = 0.0

    def _apply_rate_limit(self) -> None:
        """Sunucuyu yormamak için istekler arasına bekleme koyar."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()

    async def _apply_rate_limit_async(self) -> None:
        """Asenkron nezaketli bekleme."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            await asyncio.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()

    def fetch(self, source: SourceDefinition) -> tuple[bytes, dict[str, Any]]:
        """Senkron olarak resmî kaynağı indirir ve yanıt üstverisini döner."""
        self._apply_rate_limit()
        headers = {"User-Agent": self.user_agent}

        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    response = client.get(str(source.url), headers=headers)
                    response.raise_for_status()

                    ct_header = response.headers.get("content-type", "").lower()
                    is_pdf_source = source.content_type == ContentTypeEnum.PDF
                    is_pdf_content = "pdf" in ct_header or str(source.url).endswith(".pdf")
                    if is_pdf_source and not is_pdf_content:
                        raise InvalidMimeTypeError(
                            f"Beklenen PDF ancak gelen içerik türü: {ct_header}"
                        )

                    metadata = {
                        "source_id": source.id,
                        "url": str(source.url),
                        "status_code": response.status_code,
                        "content_type": ct_header,
                        "fetched_at": datetime.now(UTC).isoformat(),
                        "headers": dict(response.headers),
                    }
                    return response.content, metadata

            except (httpx.TimeoutException, httpx.ConnectTimeout) as e:
                last_exception = ScraperTimeoutError(f"Zaman aşımı: {source.url} - {e}")
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                last_exception = ScraperClientError(f"HTTP isteği başarısız: {e}")

            retries += 1
            if retries <= self.max_retries:
                backoff_time = self.rate_limit_seconds * (2 ** (retries - 1))
                logger.warning(
                    "İstek yeniden deneniyor (%d/%d): %s (bekleme: %.1fs)",
                    retries,
                    self.max_retries,
                    source.url,
                    backoff_time,
                )
                time.sleep(backoff_time)

        raise last_exception or ScraperClientError(f"Maksimum deneme aşıldı: {source.url}")


class SnapshotWriter:
    """İndirilen ham resmî belgeleri data/raw/{source_id}/{timestamp}/ dizininde saklar."""

    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = Path(base_path or settings.raw_data_path)

    def write_snapshot(
        self,
        source: SourceDefinition,
        content: bytes,
        metadata: dict[str, Any],
        timestamp_str: str | None = None,
    ) -> Path:
        """Ham içeriği ve metadata.json dosyasını yazar, oluşturulan dizini döner."""
        ts = timestamp_str or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        target_dir = self.base_path / source.id / ts
        target_dir.mkdir(parents=True, exist_ok=True)

        ext = "pdf" if source.content_type == ContentTypeEnum.PDF else "html"
        content_path = target_dir / f"content.{ext}"
        metadata_path = target_dir / "metadata.json"

        content_path.write_bytes(content)
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        logger.info(
            "Ham snapshot kaydedildi: %s -> %s",
            source.id,
            str(target_dir),
            extra={"component": "SnapshotWriter", "source_id": source.id},
        )
        return target_dir
