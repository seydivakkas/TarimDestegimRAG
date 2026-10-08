from pathlib import Path
from typing import Any

from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.models.source import SourceDefinition
from tarim_destek_rag.scraper.client import ScraperClient, SnapshotWriter
from tarim_destek_rag.scraper.registry import SourceRegistry, source_registry


class ScrapeResult:
    """Tek bir kaynağın kazıma neticesi."""

    def __init__(
        self,
        source_id: str,
        success: bool,
        snapshot_dir: Path | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.source_id = source_id
        self.success = success
        self.snapshot_dir = snapshot_dir
        self.error = error
        self.metadata = metadata or {}


class ScraperOrchestrator:
    """Resmî kaynak kazıma sürecini koordine eden servis."""

    def __init__(
        self,
        registry: SourceRegistry | None = None,
        client: ScraperClient | None = None,
        writer: SnapshotWriter | None = None,
    ) -> None:
        self.registry = registry or source_registry
        self.client = client or ScraperClient()
        self.writer = writer or SnapshotWriter()

    def scrape_source(self, source: SourceDefinition) -> ScrapeResult:
        """Belirtilen tek bir kaynağı çeker ve snapshot'ını oluşturur."""
        logger.info(
            "Kaynak indirme başlatılıyor: %s (%s)",
            source.id,
            source.url,
            extra={"component": "ScraperOrchestrator", "source_id": source.id},
        )
        try:
            content, metadata = self.client.fetch(source)
            snapshot_dir = self.writer.write_snapshot(source, content, metadata)
            return ScrapeResult(
                source_id=source.id,
                success=True,
                snapshot_dir=snapshot_dir,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(
                "Kaynak indirme hatası: %s - %s",
                source.id,
                e,
                extra={"component": "ScraperOrchestrator", "source_id": source.id},
            )
            return ScrapeResult(source_id=source.id, success=False, error=str(e))

    def scrape_all_active(self) -> list[ScrapeResult]:
        """Kayıtlı ve aktif tüm kaynakları sırayla indirir."""
        active_sources = self.registry.list_active_sources()
        results: list[ScrapeResult] = []
        for src in active_sources:
            res = self.scrape_source(src)
            results.append(res)
        return results
