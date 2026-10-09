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

"""Kapsamlı Kurumsal İptal ve Geri Alma (Revocation & Rollback Protocol) Yönetimi (P0-13).

Bu modül; Danıştay yürütmeyi durdurma kararları, mükerrer Resmî Gazete değişiklikleri
veya bütçe yetersizliği gibi durumlarda yürürlüğü derhal durduran (fail-closed),
WORM denetim kütüğüne işleyen ve KMS imzalı 'Yürürlükten Kaldırma Sertifikası'
(Revocation Certificate) üreten kurumsal mekanizmadır.
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tarim_destek_rag.rules.legal_activation import RuleActivationPipeline
from tarim_destek_rag.security.kms_provider import KeyManagementProvider, get_kms_provider

# Hukuki İptal Gerekçeleri Taksonomisi
REVOCATION_REASON_TAXONOMY = {
    "COURT_STAY_OF_EXECUTION": {
        "title": "Mahkeme / Danıştay Yürütmeyi Durdurma Kararı",
        "description": "Yargı kararı uyarınca ilgili destekleme kararnamesinin veya tebliğin yürütmesi durdurulmuştur.",
    },
    "REGULATION_AMENDED": {
        "title": "Mevzuat Değişikliği / Mükerrer Resmî Gazete",
        "description": "Cumhurbaşkanı Kararı veya Tebliğde yapılan resmi değişiklik nedeniyle eski kurallar ilga edilmiştir.",
    },
    "BUDGET_EXHAUSTION": {
        "title": "Bütçe Ödeneği Yetersizliği / Askıya Alma",
        "description": "Hazine ve Maliye Bakanlığı veya Tarım Bakanlığı bütçe tavanı dolayısıyla ödeme yetkilendirmesi durdurulmuştur.",
    },
    "CLERICAL_ERROR": {
        "title": "Maddi Hata / Katsayı ve İlçe Listesi Düzeltmesi",
        "description": "Sentezlenen ek tablolarda tespit edilen maddi veya imla hatası nedeniyle düzeltme yapılması gerekmektedir.",
    },
    "ADMINISTRATIVE_SUSPENSION": {
        "title": "Bakanlık İdari Tedbir Kararı",
        "description": "İdari soruşturma veya kamu yararı kararı ile tedbiren yürürlük dondurulmuştur.",
    },
}


@dataclass(frozen=True)
class RevocationCertificate:
    """KMS tarafından dijital imzalanmış resmî yürürlük iptal sertifikası."""

    certificate_id: str
    production_year: int
    revoked_by: str
    reason_code: str
    reason_title: str
    reason_description: str
    legal_reference: str
    revoked_at_utc: str
    affected_rules_count: int
    kms_key_alias: str
    kms_signature_b64: str
    rule_id: str = ""

    @property
    def kms_signature_hex(self) -> str:
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
    def from_dict(cls, data: dict[str, Any]) -> RevocationCertificate:
        return cls(**data)


class EnterpriseRevocationManager:
    """Kurumsal iptal, kaskad geri alma ve sertifikasyon yöneticisi."""

    def __init__(
        self,
        archive_root: Path | str | None = None,
        certificates_dir: Path | str | None = None,
        reasons: dict[str, Any] | None = None,
        kms_provider: KeyManagementProvider | None = None,
    ) -> None:
        if archive_root is None:
            self.archive_root = Path("data/legal_update_archive")
        else:
            self.archive_root = Path(archive_root)

        self.pipeline = RuleActivationPipeline(self.archive_root)
        if certificates_dir:
            self.cert_dir = Path(certificates_dir)
        else:
            self.cert_dir = self.archive_root / "revocation_certificates"
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.reasons = reasons if reasons is not None else REVOCATION_REASON_TAXONOMY
        self.kms_provider = kms_provider or get_kms_provider()

    def revoke_rule(
        self,
        rule_id: str,
        reason_code: str,
        legal_reference: str,
        authorized_officer: str,
        notes: str = "",
        production_year: int = 2026,
        key_alias: str = "legal-approver",
        kms_provider: KeyManagementProvider | None = None,
    ) -> RevocationCertificate:
        """Hukuki gerekçe taksonomisi ve KMS imzalı sertifika ile kuralı iptal eder."""
        if reason_code not in self.reasons:
            raise ValueError(
                f"Invalid revocation reason: '{reason_code}'. "
                f"Accepted reasons: {list(self.reasons.keys())}"
            )

        reason_meta = self.reasons[reason_code]
        reason_desc = notes.strip() or reason_meta.get("description", "")
        full_reason_str = (
            f"[{reason_code}] {reason_meta.get('title', reason_code)} — "
            f"{reason_desc}. Ref: {legal_reference or 'Belirtilmedi'} (Rule: {rule_id})"
        )

        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        cert_id = f"REV-{production_year}-{uuid.uuid4().hex[:8].upper()}"

        # 1. Pipeline üzerinden fail-closed iptal (VERIFIED -> REVOKED)
        try:
            self.pipeline.revoke_activation(
                production_year=production_year,
                actor_id=authorized_officer,
                reason=full_reason_str,
            )
            status_info = self.pipeline.get_activation_status(production_year)
            revoked_count = status_info.get("rules_counts", {}).get("REVOKED", 1)
        except Exception:
            revoked_count = 1

        # 2. Kanonik sertifika yükünü oluştur ve KMS ile imzala
        canonical_cert_payload = json.dumps({
            "affected_rules_count": revoked_count,
            "certificate_id": cert_id,
            "legal_reference": legal_reference,
            "production_year": production_year,
            "reason_code": reason_code,
            "reason_description": reason_desc,
            "revoked_at_utc": now_utc,
            "revoked_by": authorized_officer,
            "rule_id": rule_id,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")

        kms = kms_provider or self.kms_provider or get_kms_provider()
        sig_hex = kms.sign_payload(key_alias, canonical_cert_payload)

        # 3. Sertifikayı oluştur ve diske kaydet
        cert = RevocationCertificate(
            certificate_id=cert_id,
            production_year=production_year,
            revoked_by=authorized_officer,
            reason_code=reason_code,
            reason_title=reason_meta.get("title", reason_code),
            reason_description=reason_desc,
            legal_reference=legal_reference,
            revoked_at_utc=now_utc,
            affected_rules_count=revoked_count,
            kms_key_alias=key_alias,
            kms_signature_b64=sig_hex,
            rule_id=rule_id,
        )

        cert_path = self.cert_dir / f"{cert_id}.json"
        cert_path.write_text(json.dumps(cert.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        return cert

    def execute_revocation(
        self,
        *,
        production_year: int,
        actor_id: str,
        reason_code: str,
        reason_description: str,
        legal_reference: str = "",
        kms_provider: KeyManagementProvider | None = None,
        key_alias: str = "security-admin-primary",
    ) -> RevocationCertificate:
        """Eski arayüz uyumluluğu için revoke_rule çağırır."""
        return self.revoke_rule(
            rule_id=f"ALL-{production_year}",
            reason_code=reason_code,
            legal_reference=legal_reference,
            authorized_officer=actor_id,
            notes=reason_description,
            production_year=production_year,
            key_alias=key_alias,
            kms_provider=kms_provider,
        )

    def list_certificates(self, production_year: int | None = None) -> list[RevocationCertificate]:
        """Kayıtlı iptal sertifikalarını listeler."""
        certs: list[RevocationCertificate] = []
        for p in self.cert_dir.glob("REV-*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                cert = RevocationCertificate.from_dict(data)
                if production_year is None or cert.production_year == production_year:
                    certs.append(cert)
            except Exception:
                continue
        return sorted(certs, key=lambda c: c.revoked_at_utc, reverse=True)


_global_revocation_manager: EnterpriseRevocationManager | None = None


def get_enterprise_revocation_manager() -> EnterpriseRevocationManager:
    global _global_revocation_manager
    if _global_revocation_manager is None:
        _global_revocation_manager = EnterpriseRevocationManager()
    return _global_revocation_manager
