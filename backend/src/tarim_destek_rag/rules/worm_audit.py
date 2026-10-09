# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
# amaçlı olarak paylaşılmıştır.
#
# YASAKLAR:
#   1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
#   2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
#   3. Alt lisanslanamaz, satılamaz veya devredilemez.
#   4. Tersine mühendislik yapılamaz.
#
# İZİN VERİLEN KULLANIM:
#   - GitHub üzerinde görüntüleme ve okuma.
#   - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).
#
# YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
# İzin talepleri için: GitHub @seydivakkas

"""Kriptografik Değiştirilemez WORM (Write-Once-Read-Many) Denetim İzi Hattı (P0-12).

Bu modül, mevzuat onay ve aktivasyon işlemlerinin değiştirilemez, SHA-256 zincirli
ve zaman damgalı WORM denetim günlüğünü yönetir.
Herhangi bir manipülasyon veya sıra bozulması durumunda fail-closed ilkesi gereği
TamperedAuditError fırlatılır.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TamperedAuditError(Exception):
    """WORM denetim günlüğünde zincir bütünlüğü bozulduğunda fırlatılır."""


GENESIS_PREVIOUS_HASH = "0" * 64


@dataclass(frozen=True)
class WormBlock:
    """Kriptografik olarak zincirlenmiş tek bir WORM denetim bloğu."""

    block_index: int
    event_id: str
    timestamp_utc: str
    production_year: int
    event_type: str  # "GENESIS", "ATTESTATION_REVIEW", "ATTESTATION_APPROVAL", "RULE_ACTIVATION", "RULE_REVOCATION"
    actor_id: str
    role: str  # "SYSTEM", "LEGAL_REVIEWER", "LEGAL_APPROVER", "ADMIN"
    manifest_sha256: str
    signature_b64: str | None = None
    public_key_b64: str | None = None
    previous_block_sha256: str = GENESIS_PREVIOUS_HASH
    metadata: dict[str, Any] = field(default_factory=dict)
    block_sha256: str = ""

    def payload_for_hashing(self) -> dict[str, Any]:
        """Blok hash'i hesaplanırken kullanılan kanonik veri sözlüğü."""
        return {
            "block_index": self.block_index,
            "event_id": self.event_id,
            "timestamp_utc": self.timestamp_utc,
            "production_year": self.production_year,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "role": self.role,
            "manifest_sha256": self.manifest_sha256,
            "signature_b64": self.signature_b64,
            "public_key_b64": self.public_key_b64,
            "previous_block_sha256": self.previous_block_sha256,
            "metadata": self.metadata,
        }

    def compute_hash(self) -> str:
        """Kanonik JSON serileştirmesi üzerinden SHA-256 özetini üretir."""
        canonical_json = json.dumps(
            self.payload_for_hashing(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical_json).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WormBlock:
        return cls(
            block_index=data["block_index"],
            event_id=data["event_id"],
            timestamp_utc=data["timestamp_utc"],
            production_year=data["production_year"],
            event_type=data["event_type"],
            actor_id=data["actor_id"],
            role=data["role"],
            manifest_sha256=data["manifest_sha256"],
            signature_b64=data.get("signature_b64"),
            public_key_b64=data.get("public_key_b64"),
            previous_block_sha256=data.get("previous_block_sha256", GENESIS_PREVIOUS_HASH),
            metadata=data.get("metadata", {}),
            block_sha256=data.get("block_sha256", ""),
        )


class WormAuditLog:
    """Kriptografik hash zincirli, eklemeli (append-only) WORM denetim kütüğü yöneticisi."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        if base_dir is None:
            self.base_dir = Path("data/legal_update_archive/worm_audit")
        else:
            p = Path(base_dir)
            self.base_dir = p / "worm_audit" if not str(p).endswith("worm_audit") else p
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.base_dir / "audit_chain.jsonl"
        self._ensure_genesis()

    def _ensure_genesis(self) -> None:
        """Kütük boş ise başlangıç (Genesis) bloğunu oluşturur."""
        if not self.log_file.exists() or self.log_file.stat().st_size == 0:
            genesis = WormBlock(
                block_index=0,
                event_id="00000000-0000-0000-0000-000000000000",
                timestamp_utc="2026-01-01T00:00:00Z",
                production_year=2026,
                event_type="GENESIS",
                actor_id="SYSTEM",
                role="SYSTEM",
                manifest_sha256="0" * 64,
                signature_b64=None,
                public_key_b64=None,
                previous_block_sha256=GENESIS_PREVIOUS_HASH,
                metadata={"message": "TarimDestegimRAG Immutable WORM Audit Chain Genesis"},
            )
            block_hash = genesis.compute_hash()
            genesis_with_hash = WormBlock(
                block_index=genesis.block_index,
                event_id=genesis.event_id,
                timestamp_utc=genesis.timestamp_utc,
                production_year=genesis.production_year,
                event_type=genesis.event_type,
                actor_id=genesis.actor_id,
                role=genesis.role,
                manifest_sha256=genesis.manifest_sha256,
                signature_b64=genesis.signature_b64,
                public_key_b64=genesis.public_key_b64,
                previous_block_sha256=genesis.previous_block_sha256,
                metadata=genesis.metadata,
                block_sha256=block_hash,
            )
            line = json.dumps(genesis_with_hash.to_dict(), ensure_ascii=False) + "\n"
            self.log_file.write_text(line, encoding="utf-8")

    def load_blocks(self) -> list[WormBlock]:
        """Tüm blokları sırasıyla kütükten okur."""
        if not self.log_file.exists():
            return []
        blocks: list[WormBlock] = []
        for line in self.log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            blocks.append(WormBlock.from_dict(data))
        return blocks

    def get_latest_block(self) -> WormBlock:
        """En son kaydedilmiş bloğu döndürür."""
        blocks = self.load_blocks()
        if not blocks:
            self._ensure_genesis()
            blocks = self.load_blocks()
        return blocks[-1]

    def append_event(
        self,
        *,
        production_year: int,
        event_type: str,
        actor_id: str,
        role: str,
        manifest_sha256: str,
        signature_b64: str | None = None,
        public_key_b64: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WormBlock:
        """Yeni bir denetim olayını doğrulanmış hash zincirine atomik olarak ekler."""
        # Önce mevcut zincir bütünlüğünü doğrula (fail-closed)
        self.verify_chain()

        latest = self.get_latest_block()
        next_index = latest.block_index + 1
        previous_hash = latest.block_sha256

        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        event_id = str(uuid.uuid4())

        block_candidate = WormBlock(
            block_index=next_index,
            event_id=event_id,
            timestamp_utc=now_utc,
            production_year=production_year,
            event_type=event_type,
            actor_id=actor_id,
            role=role,
            manifest_sha256=manifest_sha256,
            signature_b64=signature_b64,
            public_key_b64=public_key_b64,
            previous_block_sha256=previous_hash,
            metadata=metadata or {},
        )
        computed_hash = block_candidate.compute_hash()

        final_block = WormBlock(
            block_index=block_candidate.block_index,
            event_id=block_candidate.event_id,
            timestamp_utc=block_candidate.timestamp_utc,
            production_year=block_candidate.production_year,
            event_type=block_candidate.event_type,
            actor_id=block_candidate.actor_id,
            role=block_candidate.role,
            manifest_sha256=block_candidate.manifest_sha256,
            signature_b64=block_candidate.signature_b64,
            public_key_b64=block_candidate.public_key_b64,
            previous_block_sha256=block_candidate.previous_block_sha256,
            metadata=block_candidate.metadata,
            block_sha256=computed_hash,
        )

        # Append-only yazma
        line = json.dumps(final_block.to_dict(), ensure_ascii=False) + "\n"
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(line)

        return final_block

    def verify_chain(self) -> tuple[bool, str]:
        """Tüm kütük zincirinin kriptografik doğruluğunu ve sırasını denetler."""
        blocks = self.load_blocks()
        if not blocks:
            raise TamperedAuditError("WORM kütüğü boş veya okunamadı.")

        # 1. Genesis kontrolü
        genesis = blocks[0]
        if genesis.block_index != 0:
            raise TamperedAuditError(f"Genesis blok indeksi 0 olmalı, bulunan: {genesis.block_index}")
        if genesis.previous_block_sha256 != GENESIS_PREVIOUS_HASH:
            raise TamperedAuditError(
                f"Genesis previous_block_sha256 geçersiz: {genesis.previous_block_sha256}"
            )
        expected_genesis_hash = genesis.compute_hash()
        if genesis.block_sha256 != expected_genesis_hash:
            raise TamperedAuditError(
                f"Genesis blok hash'i manipüle edilmiş: beklenen {expected_genesis_hash}, bulunan {genesis.block_sha256}"
            )

        # 2. Bloklar arası zincir doğrulaması
        for i in range(1, len(blocks)):
            prev = blocks[i - 1]
            curr = blocks[i]

            if curr.block_index != prev.block_index + 1:
                raise TamperedAuditError(
                    f"Blok sıra hatası (Block #{curr.block_index}): Beklenen {prev.block_index + 1}"
                )

            if curr.previous_block_sha256 != prev.block_sha256:
                raise TamperedAuditError(
                    f"Zincir kırılması (Block #{curr.block_index}): previous_block_sha256={curr.previous_block_sha256} "
                    f"önceki bloğun hash'i ile uyuşmuyor ({prev.block_sha256})"
                )

            expected_hash = curr.compute_hash()
            if curr.block_sha256 != expected_hash:
                raise TamperedAuditError(
                    f"Blok içerik manipülasyonu (Block #{curr.block_index}): "
                    f"Hesaplanan {expected_hash} != Kayıtlı {curr.block_sha256}"
                )

        return True, f"WORM zinciri kusursuz doğrulandı. Toplam {len(blocks)} blok incelendi."

    def get_history(
        self,
        production_year: int | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Denetim geçmişini filtrelere göre listeler."""
        blocks = self.load_blocks()
        results: list[dict[str, Any]] = []
        for b in reversed(blocks):
            if production_year is not None and b.production_year != production_year:
                continue
            if event_type is not None and b.event_type != event_type:
                continue
            results.append(b.to_dict())
            if len(results) >= limit:
                break
        return results
