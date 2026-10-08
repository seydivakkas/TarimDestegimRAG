from pathlib import Path

import yaml
from pydantic import ValidationError

from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.models.source import AuthorityEnum, SourceDefinition


class SourceRegistryError(Exception):
    """Kaynak kayıt defteri genel hatası."""


class DuplicateSourceIdError(SourceRegistryError):
    """Mükerrer kaynak kimliği hatası."""


class SourceNotFoundError(SourceRegistryError):
    """Kaynak bulunamadı hatası."""


class SourceRegistry:
    """Resmî kaynakların kaydedildiği, doğrulandığı ve sorgulandığı kayıt defteri."""

    def __init__(self) -> None:
        self._sources: dict[str, SourceDefinition] = {}

    def register(self, source: SourceDefinition) -> None:
        """Yeni bir kaynak kaydeder. Mükerrer ID var ise hata fırlatır."""
        if source.id in self._sources:
            raise DuplicateSourceIdError(f"Mükerrer kaynak kimliği tespit edildi: {source.id}")
        self._sources[source.id] = source
        logger.debug(
            "Kaynak deftere kaydedildi",
            extra={"component": "SourceRegistry", "source_id": source.id},
        )

    def get_source(self, source_id: str) -> SourceDefinition:
        """ID'ye göre kaynak döner."""
        if source_id not in self._sources:
            raise SourceNotFoundError(f"Kaynak bulunamadı: {source_id}")
        return self._sources[source_id]

    def list_all(self) -> list[SourceDefinition]:
        """Tüm kayıtlı kaynakları döner."""
        return list(self._sources.values())

    def list_active_sources(self) -> list[SourceDefinition]:
        """Yalnızca aktif kaynakları öncelik sırasına göre (P0 -> P3) döner."""
        active = [s for s in self._sources.values() if s.active]
        return sorted(active, key=lambda s: s.priority)

    def list_by_authority(self, authority: AuthorityEnum) -> list[SourceDefinition]:
        """Belirli bir resmî kurum kademesine ait kaynakları döner."""
        return [s for s in self._sources.values() if s.authority == authority]

    def clear(self) -> None:
        """Kayıt defterini temizler."""
        self._sources.clear()

    @classmethod
    def load_from_yaml(cls, yaml_path: str = "configs/sources.yaml") -> "SourceRegistry":
        """YAML dosyasından tüm kaynakları yükler ve doğrular."""
        registry = cls()
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Kaynak tanım dosyası bulunamadı: {yaml_path}")

        with open(path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

        raw_sources = raw_data.get("sources", [])
        for item in raw_sources:
            try:
                source = SourceDefinition(**item)
                registry.register(source)
            except ValidationError as e:
                raise SourceRegistryError(f"Kaynak şema doğrulama hatası: {e}") from e

        return registry


source_registry = SourceRegistry()
