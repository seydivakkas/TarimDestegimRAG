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

"""Gelişmiş Kurumsal WORM Arşivi ve Hukuki Delil Kasası (P0-13).

Bu modül, WORM denetim kütüğünü periyodik Merkle kök özetleriyle (Checkpoints)
mühürler, dosya sistemi bütünlük kilitlerini yönetir ve adli/hukuki denetimler için
mahkeme geçerliliğine sahip 'Hukuki Delil Paketi' (Legal Evidence Vault) üretir.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tarim_destek_rag.rules.worm_audit import WormAuditLog
from tarim_destek_rag.security.kms_provider import KeyManagementProvider, get_kms_provider


@dataclass(frozen=True)
class WormCheckpoint:
    """WORM denetim zincirinin belirli bir aralığını kriptografik olarak mühürleyen kontrol noktası."""

    checkpoint_id: str
    production_year: int
    start_block_index: int
    end_block_index: int
    root_hash: str
    created_at_utc: str
    kms_key_alias: str
    kms_signature_b64: str
    signer_officer: str = "ChiefAuditor"

    @property
    def merkle_root_hash(self) -> str:
        return self.root_hash

    @property
    def kms_signature_hex(self) -> str:
        # If it's already hex (128 chars), return it; else decode b64 to hex
        if len(self.kms_signature_b64) == 128:
            return self.kms_signature_b64
        try:
            raw = base64.b64decode(self.kms_signature_b64)
            return raw.hex()
        except Exception:
            return self.kms_signature_b64

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WormCheckpoint:
        return cls(**data)


class EnterpriseWormArchive:
    """Kurumsal WORM arşivi, mühürleme ve hukuki delil kasası yöneticisi."""

    def __init__(
        self,
        archive_root: Path | str | None = None,
        archive_dir: Path | str | None = None,
        kms_provider: KeyManagementProvider | None = None,
    ) -> None:
        target = archive_dir or archive_root
        if target is None:
            self.archive_root = Path("data/legal_update_archive")
        else:
            self.archive_root = Path(target)

        self.worm_log = WormAuditLog(self.archive_root)
        self.checkpoints_dir = self.archive_root / "worm_checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.vault_exports_dir = self.archive_root / "evidence_vault_exports"
        self.vault_exports_dir.mkdir(parents=True, exist_ok=True)
        self.kms_provider = kms_provider or get_kms_provider()

    def create_checkpoint(
        self,
        production_year: int = 2026,
        signer_officer: str = "ChiefAuditor",
        key_alias: str = "release-master",
        kms_provider: KeyManagementProvider | None = None,
    ) -> WormCheckpoint:
        """Belirtilen yılın bloklarını doğrular ve KMS imzalı kriptografik mühür oluşturur."""
        # 1. Zincir bütünlüğünü denetle
        self.worm_log.verify_chain()

        all_blocks = self.worm_log.load_blocks()
        blocks = [b for b in all_blocks if b.production_year == production_year or b.block_index == 0]
        if not blocks:
            blocks = all_blocks

        start_idx = blocks[0].block_index if blocks else 0
        end_idx = blocks[-1].block_index if blocks else 0

        # Blok hash'lerinden kümülatif kök özeti hesapla
        hasher = hashlib.sha256()
        for b in blocks:
            hasher.update(b.block_sha256.encode("ascii"))
        root_hash = hasher.hexdigest()

        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        checkpoint_id = f"CKPT-{production_year}-{uuid.uuid4().hex[:8].upper()}"

        # KMS ile mühür imzası
        kms = kms_provider or self.kms_provider or get_kms_provider()
        payload_to_sign = json.dumps({
            "checkpoint_id": checkpoint_id,
            "production_year": production_year,
            "start_block_index": start_idx,
            "end_block_index": end_idx,
            "root_hash": root_hash,
            "signer_officer": signer_officer,
            "created_at_utc": now_utc,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")

        sig_hex = kms.sign_payload(key_alias, payload_to_sign)

        checkpoint = WormCheckpoint(
            checkpoint_id=checkpoint_id,
            production_year=production_year,
            start_block_index=start_idx,
            end_block_index=end_idx,
            root_hash=root_hash,
            created_at_utc=now_utc,
            kms_key_alias=key_alias,
            kms_signature_b64=sig_hex,
            signer_officer=signer_officer,
        )

        cp_path = self.checkpoints_dir / f"{checkpoint_id}.json"
        cp_path.write_text(json.dumps(checkpoint.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return checkpoint

    def list_checkpoints(self, production_year: int | None = None) -> list[WormCheckpoint]:
        """Kayıtlı kontrol noktalarını listeler."""
        cps: list[WormCheckpoint] = []
        for p in self.checkpoints_dir.glob("CKPT-*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                cp = WormCheckpoint.from_dict(data)
                if production_year is None or cp.production_year == production_year:
                    cps.append(cp)
            except Exception:
                continue
        return sorted(cps, key=lambda c: c.created_at_utc, reverse=True)

    def export_legal_evidence_vault(
        self,
        production_year: int = 2026,
        signer_officer: str = "ChiefLegalAuditor",
        key_alias: str = "legal-approver",
        destination_dir: Path | str | None = None,
        output_dir: Path | str | None = None,
        kms_provider: KeyManagementProvider | None = None,
    ) -> Path:
        """Mahkeme ve resmi teftiş için KMS imzalı Hukuki Delil Paketi (.zip) üretir."""
        self.worm_log.verify_chain()

        target_out = output_dir or destination_dir or self.vault_exports_dir
        dest = Path(target_out)
        dest.mkdir(parents=True, exist_ok=True)

        now_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
        zip_path = dest / f"EVIDENCE_VAULT_{production_year}_{now_str}.zip"

        # Dosyaları topla
        manifest_file = self.archive_root / "activation_manifests" / f"manifest_{production_year}.json"
        rules_file = self.archive_root / "rules_catalog" / f"rules_{production_year}.json"
        audit_file = self.archive_root / "worm_audit" / "audit_chain.jsonl"

        manifest_content = manifest_file.read_bytes() if manifest_file.is_file() else b"{}"
        rules_content = rules_file.read_bytes() if rules_file.is_file() else b"[]"
        audit_content = audit_file.read_bytes() if audit_file.is_file() else b""

        # Denetim raporu metni
        verified, ver_msg = self.worm_log.verify_chain()
        report_data = {
            "title": "TARIMDESTEK RAG HUKUKI DELIL VE MEVZUAT DOGRULAMA RAPORU",
            "production_year": production_year,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "worm_chain_verified": verified,
            "verification_message": ver_msg,
            "fail_closed_policy": "ACTIVE",
            "signer_officer": signer_officer,
        }
        report_bytes = json.dumps(report_data, indent=2, ensure_ascii=False).encode("utf-8")

        # Dosya özetleri listesi (sha256sums.txt)
        sums = {
            "manifest.json": hashlib.sha256(manifest_content).hexdigest(),
            "rules.json": hashlib.sha256(rules_content).hexdigest(),
            "worm_audit_chain.jsonl": hashlib.sha256(audit_content).hexdigest(),
            "verification_report.json": hashlib.sha256(report_bytes).hexdigest(),
        }

        sums_text = "".join(f"{h}  {name}\n" for name, h in sorted(sums.items())).encode("utf-8")

        # KMS İmzası
        kms = kms_provider or self.kms_provider or get_kms_provider()
        seal_sig_hex = kms.sign_payload(key_alias, sums_text)
        seal_info = json.dumps({
            "production_year": production_year,
            "signer_officer": signer_officer,
            "kms_key_alias": key_alias,
            "signed_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sha256sums_hash": hashlib.sha256(sums_text).hexdigest(),
            "kms_signature_hex": seal_sig_hex,
            "sha256sums": sums,
            "status": "COURT_READY_SEALED",
        }, indent=2, ensure_ascii=False).encode("utf-8")

        # Zip dosyasını inşa et
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", manifest_content)
            zf.writestr("rules.json", rules_content)
            zf.writestr("worm_audit_chain.jsonl", audit_content)
            zf.writestr("verification_report.json", report_bytes)
            zf.writestr("sha256sums.txt", sums_text)
            zf.writestr("evidence_package_seal.json", seal_info)

        return zip_path


_global_enterprise_worm_archive: EnterpriseWormArchive | None = None


def get_enterprise_worm_archive() -> EnterpriseWormArchive:
    global _global_enterprise_worm_archive
    if _global_enterprise_worm_archive is None:
        _global_enterprise_worm_archive = EnterpriseWormArchive()
    return _global_enterprise_worm_archive
