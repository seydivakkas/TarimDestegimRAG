from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from tarim_destek_rag.change_detector.hasher import compute_content_hash
from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.models.source import ContentTypeEnum, SourceDefinition


class ChangeStatusEnum(StrEnum):
    """Değişiklik durumu enum'ı."""

    NEW = "NEW"  # İlk kez keşfedilen kaynak
    UNCHANGED = "UNCHANGED"  # İçerik özeti birebir aynı
    UPDATED = "UPDATED"  # İçerik değişti, yeni versiyon adayı
    REMOVED = "REMOVED"  # Kaynak yayından kalktı / ulaşılamıyor


class VersionEvent(BaseModel):
    """Mevzuat sürüm değişiklik olayı kaydı (Audit Store)."""

    source_id: str
    old_hash: str | None = None
    new_hash: str | None = None
    status: ChangeStatusEnum
    detected_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    superseded_candidate: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChangeDetector:
    """Kayıtlı önceki özetler ile yeni indirilen içeriği karşılaştıran dedektör."""

    def __init__(self, current_hashes: dict[str, str] | None = None) -> None:
        # source_id -> content_hash haritası
        self._current_hashes: dict[str, str] = current_hashes or {}
        self._history: list[VersionEvent] = []

    def get_known_hash(self, source_id: str) -> str | None:
        """Kayıtlı bilinen özeti döner."""
        return self._current_hashes.get(source_id)

    def evaluate(
        self,
        source: SourceDefinition,
        raw_content: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> VersionEvent:
        """Yeni ham içeriği analiz eder, değişiklik olayını döner ve geçmişe kaydeder."""
        is_html = source.content_type == ContentTypeEnum.HTML
        new_hash = compute_content_hash(raw_content, is_html=is_html)
        old_hash = self.get_known_hash(source.id)

        if old_hash is None:
            status = ChangeStatusEnum.NEW
            superseded = False
        elif old_hash == new_hash:
            status = ChangeStatusEnum.UNCHANGED
            superseded = False
        else:
            status = ChangeStatusEnum.UPDATED
            superseded = True  # Eski veri silinmez, superseded adayı olur

        event = VersionEvent(
            source_id=source.id,
            old_hash=old_hash,
            new_hash=new_hash,
            status=status,
            superseded_candidate=superseded,
            metadata=metadata or {},
        )

        # Aktif özeti güncelle
        self._current_hashes[source.id] = new_hash
        self._history.append(event)

        logger.info(
            "Kaynak sürüm durumu tespit edildi: %s -> %s (superseded=%s)",
            source.id,
            status.value,
            superseded,
            extra={"component": "ChangeDetector", "source_id": source.id},
        )
        return event

    def get_events(self, source_id: str | None = None) -> list[VersionEvent]:
        """Kayıtlı olay geçmişini döner."""
        if source_id:
            return [e for e in self._history if e.source_id == source_id]
        return list(self._history)
