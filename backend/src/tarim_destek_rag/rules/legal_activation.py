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

"""Çift Onaylı Hukuki İnceleme & WORM Aktivasyon Hattı (P0-12).

Bu modül, dinamik kural ve fiyatların yürürlüğe alınmasında iki bağımsız yetkilinin
(LEGAL_REVIEWER ve LEGAL_APPROVER) Ed25519 asimetrik imzalarını doğrular,
görevler ayrılığı (Separation of Duties) ilkesini zorunlu kılar ve WORM kütüğüne
kriptografik blok olarak kaydederek kuralları DRAFT durumundan VERIFIED durumuna
atomik olarak yükseltir.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository
from tarim_destek_rag.rules.worm_audit import TamperedAuditError, WormAuditLog

# Standart hukuk tasdiki beyan metni şablonu
STANDARD_ATTESTATION_STATEMENT = (
    "{year} yılı tarımsal destekleme kuralları, Cumhurbaşkanı Kararı ve ilgili tebliğ "
    "hükümleri uyarınca incelenmiş ve doğrulanmıştır."
)

TRUST_ENV = "TARIM_RAG_LEGAL_TRUSTED_KEYS_JSON"


class ActivationError(Exception):
    """Aktivasyon sürecindeki genel hatalar için temel sınıf."""


class SeparationOfDutiesViolation(ActivationError):
    """İnceleyen ve onaylayan kişi veya anahtar aynı olduğunda fırlatılır."""


class InvalidSignatureError(ActivationError):
    """Ed25519 dijital imzası doğrulanamadığında fırlatılır."""


class DigestMismatchError(ActivationError):
    """Kural özeti veya kaynak belge özeti uyuşmadığında fırlatılır."""


class TrustedKeyMismatchError(ActivationError):
    """İmzalayan anahtar kayıtlı güvenilir anahtar deposunda bulunamadığında fırlatılır."""


# ---------------------------------------------------------------------------
# Kriptografik Yardımcılar
# ---------------------------------------------------------------------------

def generate_ed25519_keypair() -> tuple[str, str]:
    """Test ve yetkili tanımlama için yeni Ed25519 anahtar çifti üretir.

    Returns:
        (private_key_b64, public_key_b64)
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_raw = private_key.private_bytes_raw()
    pub_raw = public_key.public_bytes_raw()

    priv_b64 = base64.b64encode(priv_raw).decode("ascii")
    pub_b64 = base64.b64encode(pub_raw).decode("ascii")
    return priv_b64, pub_b64


def sign_payload_ed25519(private_key_b64: str, payload_bytes: bytes) -> str:
    """Verilen kanonik bayt dizisini Ed25519 özel anahtarı ile imzalar."""
    priv_raw = base64.b64decode(private_key_b64.encode("ascii"))
    private_key = Ed25519PrivateKey.from_private_bytes(priv_raw)
    signature = private_key.sign(payload_bytes)
    return base64.b64encode(signature).decode("ascii")


def verify_signature_ed25519(
    public_key_b64: str,
    signature_b64: str,
    payload_bytes: bytes,
) -> bool:
    """Ed25519 imzasının doğruluğunu denetler."""
    try:
        pub_raw = base64.b64decode(public_key_b64.encode("ascii"))
        sig_raw = base64.b64decode(signature_b64.encode("ascii"))
        if len(pub_raw) != 32 or len(sig_raw) != 64:
            return False
        public_key = Ed25519PublicKey.from_public_bytes(pub_raw)
        public_key.verify(sig_raw, payload_bytes)
        return True
    except (InvalidSignature, binascii.Error, ValueError):
        return False


def build_canonical_manifest_bytes(
    production_year: int,
    source_document_sha256: str,
    rules_digest: str,
    rule_count: int,
    statement: str,
) -> bytes:
    """İmzalanacak kanonik beyan yükünü deterministik olarak oluşturur."""
    payload = {
        "attestation_statement": statement,
        "production_year": production_year,
        "rule_count": rule_count,
        "rules_digest": rules_digest,
        "source_document_sha256": source_document_sha256,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Veri Modelleri
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LegalAttestation:
    """Tek bir yetkilinin (Hukuk Müşaviri veya Harcama Yetkilisi) dijital tasdiki."""

    actor_id: str
    role: str  # "LEGAL_REVIEWER" veya "LEGAL_APPROVER"
    public_key_b64: str
    signature_b64: str
    signed_at: str
    statement: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegalAttestation:
        return cls(
            actor_id=data["actor_id"],
            role=data["role"],
            public_key_b64=data["public_key_b64"],
            signature_b64=data["signature_b64"],
            signed_at=data["signed_at"],
            statement=data["statement"],
            notes=data.get("notes", ""),
        )


@dataclass(frozen=True)
class ActivationManifest:
    """Çift onaylı ve WORM kayıtlı yürürlük aktivasyon manifestosu."""

    manifest_id: str
    production_year: int
    source_document_sha256: str
    rules_digest: str
    rule_count: int
    status: str  # "ACTIVE", "REVOKED", "HOLD"
    activated_at: str
    reviewer_attestation: LegalAttestation
    approver_attestation: LegalAttestation
    worm_block_sha256: str
    revocation_info: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "production_year": self.production_year,
            "source_document_sha256": self.source_document_sha256,
            "rules_digest": self.rules_digest,
            "rule_count": self.rule_count,
            "status": self.status,
            "activated_at": self.activated_at,
            "reviewer_attestation": self.reviewer_attestation.to_dict(),
            "approver_attestation": self.approver_attestation.to_dict(),
            "worm_block_sha256": self.worm_block_sha256,
            "revocation_info": self.revocation_info,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActivationManifest:
        return cls(
            manifest_id=data["manifest_id"],
            production_year=data["production_year"],
            source_document_sha256=data["source_document_sha256"],
            rules_digest=data["rules_digest"],
            rule_count=data["rule_count"],
            status=data["status"],
            activated_at=data["activated_at"],
            reviewer_attestation=LegalAttestation.from_dict(data["reviewer_attestation"]),
            approver_attestation=LegalAttestation.from_dict(data["approver_attestation"]),
            worm_block_sha256=data["worm_block_sha256"],
            revocation_info=data.get("revocation_info"),
        )


# ---------------------------------------------------------------------------
# Aktivasyon Hattı Motoru
# ---------------------------------------------------------------------------

class RuleActivationPipeline:
    """Çift onaylı hukuki inceleme, WORM kaydı ve kuralları yürürlüğe alma motoru."""

    def __init__(self, archive_root: Path | str | None = None) -> None:
        if archive_root is None:
            self.archive_root = Path("data/legal_update_archive")
        else:
            self.archive_root = Path(archive_root)

        self.worm_log = WormAuditLog(self.archive_root)
        self.rule_repo = DynamicRuleRepository(self.archive_root)
        self.manifest_dir = self.archive_root / "activation_manifests"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

    def _manifest_path(self, year: int) -> Path:
        return self.manifest_dir / f"manifest_{year}.json"

    def get_manifest(self, year: int) -> ActivationManifest | None:
        """Belirtilen yılın kayıtlı aktivasyon manifestosunu yükler."""
        path = self._manifest_path(year)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ActivationManifest.from_dict(data)
        except Exception:
            return None

    def save_manifest(self, manifest: ActivationManifest) -> Path:
        """Manifestoyu atomik olarak diske kaydeder."""
        target = self._manifest_path(manifest.production_year)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(target)
        return target

    def _load_trusted_store(self, custom_keys: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Trust roots must be server provisioned, never replaced by API input."""
        test_profile = os.getenv("TARIM_RAG_LEGAL_SECURITY_PROFILE") == "isolated_test"
        if custom_keys is not None and not test_profile:
            raise TrustedKeyMismatchError("Request-supplied trusted keys are forbidden")
        if custom_keys is not None:
            return custom_keys
        raw_env = os.getenv(TRUST_ENV)
        if not raw_env:
            return None
        try:
            keys = json.loads(raw_env)
            if not isinstance(keys, dict):
                raise ValueError("Trust store must be a dictionary")
            return keys
        except (ValueError, TypeError) as exc:
            raise TrustedKeyMismatchError("Invalid configured trusted key registry") from exc

    @staticmethod
    def _role_key(store: dict[str, Any], role: str) -> str | None:
        name = "reviewer" if role == "LEGAL_REVIEWER" else "approver"
        row = store.get(name)
        value = row.get("public_key_b64") if isinstance(row, dict) else store.get(role)
        return value if isinstance(value, str) and value else None

    def active_release_is_verified(self, production_year: int) -> bool:
        """Independent per-read gate for payment/denial, including revocation.

        JSON VERIFIED labels, local WORM hashes and valid self-signed keys do
        not by themselves constitute a trusted legal release.
        """
        if (
            os.getenv("TARIM_RAG_LEGAL_ACTIVATION_ENABLED") != "true"
            or os.getenv("TARIM_RAG_LEGAL_SECURITY_PROFILE") != "production"
        ):
            return False
        try:
            store = self._load_trusted_store()
            if not store:
                return False
            rev_key = self._role_key(store, "LEGAL_REVIEWER")
            app_key = self._role_key(store, "LEGAL_APPROVER")
            if not rev_key or not app_key or rev_key == app_key:
                return False
            manifest = self.get_manifest(production_year)
            rules = self.rule_repo.load_rules(production_year)
            if (
                manifest is None or manifest.status != "ACTIVE"
                or manifest.production_year != production_year
                or not rules or len(rules) != manifest.rule_count
                or any(r.get("review_status") != "VERIFIED" for r in rules)
            ):
                return False
            reviewer, approver = manifest.reviewer_attestation, manifest.approver_attestation
            if (
                reviewer.role != "LEGAL_REVIEWER" or approver.role != "LEGAL_APPROVER"
                or reviewer.actor_id == approver.actor_id
                or reviewer.public_key_b64 != rev_key
                or approver.public_key_b64 != app_key
            ):
                return False

            # The signed manifest contains the pre-activation DRAFT digest;
            # status-only transition to VERIFIED must not invalidate it.
            canonical = sorted(
                (dict(r, review_status="DRAFT") for r in rules),
                key=lambda r: r.get("rule_id", ""),
            )
            raw = json.dumps(
                canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            if hashlib.sha256(raw).hexdigest() != manifest.rules_digest:
                return False
            for att in (reviewer, approver):
                message = build_canonical_manifest_bytes(
                    production_year, manifest.source_document_sha256,
                    manifest.rules_digest, manifest.rule_count, att.statement,
                )
                if not verify_signature_ed25519(
                    att.public_key_b64, att.signature_b64, message,
                ):
                    return False
            if not isinstance(manifest.source_document_sha256, str):
                return False
            sha = manifest.source_document_sha256
            if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
                return False
            originals = self.archive_root / "originals"
            if not any(
                hashlib.sha256(p.read_bytes()).hexdigest() == sha
                for p in (originals / (sha + ".pdf"), originals / (sha + ".html"))
                if p.is_file()
            ):
                return False
            ok, _ = self.worm_log.verify_chain()
            if not ok:
                return False
            blocks = self.worm_log.load_blocks()
            matches = [
                b for b in blocks if b.event_type == "RULE_ACTIVATION"
                and b.production_year == production_year
                and b.block_sha256 == manifest.worm_block_sha256
                and b.manifest_sha256 == manifest.rules_digest
                and b.metadata.get("manifest_id") == manifest.manifest_id
                and b.metadata.get("source_sha256") == sha
            ]
            if len(matches) != 1:
                return False
            return not any(
                b.event_type == "RULE_REVOCATION"
                and b.production_year == production_year
                and b.block_index > matches[0].block_index for b in blocks
            )
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, TamperedAuditError):
            return False


    def activate_rules(
        self,
        *,
        production_year: int,
        reviewer_attestation: LegalAttestation,
        approver_attestation: LegalAttestation,
        source_document_sha256: str,
        trusted_keys: dict[str, Any] | None = None,
    ) -> ActivationManifest:
        """İki yetkilinin imzasını doğrular ve kuralları yürürlüğe alır (DRAFT -> VERIFIED).

        Adımlar:
          1. WORM denetim günlüğü bütünlüğünü doğrula.
          2. Görevler ayrılığı (Separation of Duties) kontrolü.
          3. Kuralların varlığını ve özetini (rules_digest) doğrula.
          4. Güvenilir anahtar deposu kontrolü (yapılandırılmışsa).
          5. Ed25519 imzalarının doğrulanması.
          6. WORM denetim günlüğüne olayların eklenmesi.
          7. Kuralların 'VERIFIED' durumuna yükseltilmesi.
          8. Aktivasyon manifestosunun kaydedilmesi.
        """
        # 1. WORM Bütünlük Doğrulaması (Fail-Closed)
        self.worm_log.verify_chain()

        # 2. Görevler Ayrılığı (Separation of Duties)
        if reviewer_attestation.actor_id == approver_attestation.actor_id:
            raise SeparationOfDutiesViolation(
                f"Görevler ayrılığı ihlali: İnceleyen ve Onaylayan aynı aktör olamaz ({reviewer_attestation.actor_id})."
            )
        if reviewer_attestation.public_key_b64 == approver_attestation.public_key_b64:
            raise SeparationOfDutiesViolation(
                "Görevler ayrılığı ihlali: İnceleyen ve Onaylayan aynı genel anahtarı kullanamaz."
            )
        if reviewer_attestation.role != "LEGAL_REVIEWER":
            raise SeparationOfDutiesViolation(
                f"İnceleyen rolü 'LEGAL_REVIEWER' olmalıdır, gelen: {reviewer_attestation.role}"
            )
        if approver_attestation.role != "LEGAL_APPROVER":
            raise SeparationOfDutiesViolation(
                f"Onaylayan rolü 'LEGAL_APPROVER' olmalıdır, gelen: {approver_attestation.role}"
            )

        # 3. Kural Varlığı ve Özet Kontrolü
        rules = self.rule_repo.load_rules(production_year)
        if not rules:
            raise ActivationError(
                f"{production_year} yılı için depoda kayıtlı kural bulunamadı. Önce kural sentezi yapılmalıdır."
            )

        calculated_rules_digest = self.rule_repo.compute_rules_digest(production_year)

        # Kanonik beyan baytları
        canonical_bytes = build_canonical_manifest_bytes(
            production_year=production_year,
            source_document_sha256=source_document_sha256,
            rules_digest=calculated_rules_digest,
            rule_count=len(rules),
            statement=reviewer_attestation.statement,
        )

        # 4. Trust roots are mandatory in production. Untrusted callers must
        # never bring their own accepted signer keys or activate local fixtures.
        test_profile = os.getenv("TARIM_RAG_LEGAL_SECURITY_PROFILE") == "isolated_test"
        if not test_profile and os.getenv("TARIM_RAG_LEGAL_ACTIVATION_ENABLED") != "true":
            raise ActivationError("Production legal activation is disabled")
        trust_store = self._load_trusted_store(trusted_keys)
        if not test_profile and (
            not trust_store
            or not self._role_key(trust_store, "LEGAL_REVIEWER")
            or not self._role_key(trust_store, "LEGAL_APPROVER")
        ):
            raise TrustedKeyMismatchError("Independent server-trusted reviewer and approver required")
        if trust_store:
            # Format: {"reviewer": {"public_key_b64": "..."}, "approver": {"public_key_b64": "..."}}
            # veya doğrudan role göre: {"LEGAL_REVIEWER": "...", "LEGAL_APPROVER": "..."}
            trusted_rev = self._role_key(trust_store, "LEGAL_REVIEWER")
            trusted_app = self._role_key(trust_store, "LEGAL_APPROVER")
            if trusted_rev and reviewer_attestation.public_key_b64 != trusted_rev:
                raise TrustedKeyMismatchError(
                    f"İnceleyen anahtarı güvenilir anahtar deposu ile eşleşmiyor: {reviewer_attestation.public_key_b64}"
                )
            if trusted_app and approver_attestation.public_key_b64 != trusted_app:
                raise TrustedKeyMismatchError(
                    f"Onaylayan anahtarı güvenilir anahtar deposu ile eşleşmiyor: {approver_attestation.public_key_b64}"
                )

        # 5. Ed25519 İmzalarının Doğrulanması
        if not verify_signature_ed25519(
            public_key_b64=reviewer_attestation.public_key_b64,
            signature_b64=reviewer_attestation.signature_b64,
            payload_bytes=canonical_bytes,
        ):
            raise InvalidSignatureError("İnceleyen (LEGAL_REVIEWER) Ed25519 imzası geçersiz.")

        # Onaylayanın da aynı kanonik baytları imzaladığını doğrula (veya kendi beyanıyla)
        approver_bytes = build_canonical_manifest_bytes(
            production_year=production_year,
            source_document_sha256=source_document_sha256,
            rules_digest=calculated_rules_digest,
            rule_count=len(rules),
            statement=approver_attestation.statement,
        )
        if not verify_signature_ed25519(
            public_key_b64=approver_attestation.public_key_b64,
            signature_b64=approver_attestation.signature_b64,
            payload_bytes=approver_bytes,
        ):
            raise InvalidSignatureError("Onaylayan (LEGAL_APPROVER) Ed25519 imzası geçersiz.")

        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest_id = f"MANIFEST-{production_year}-{uuid.uuid4().hex[:8].upper()}"

        # 6. WORM Denetim Günlüğüne Kayıt
        # 6a. İnceleme Olayı
        self.worm_log.append_event(
            production_year=production_year,
            event_type="ATTESTATION_REVIEW",
            actor_id=reviewer_attestation.actor_id,
            role=reviewer_attestation.role,
            manifest_sha256=calculated_rules_digest,
            signature_b64=reviewer_attestation.signature_b64,
            public_key_b64=reviewer_attestation.public_key_b64,
            metadata={"notes": reviewer_attestation.notes, "rules_count": len(rules)},
        )

        # 6b. Onay Olayı
        self.worm_log.append_event(
            production_year=production_year,
            event_type="ATTESTATION_APPROVAL",
            actor_id=approver_attestation.actor_id,
            role=approver_attestation.role,
            manifest_sha256=calculated_rules_digest,
            signature_b64=approver_attestation.signature_b64,
            public_key_b64=approver_attestation.public_key_b64,
            metadata={"notes": approver_attestation.notes, "rules_count": len(rules)},
        )

        # 6c. Aktivasyon Olayı
        act_block = self.worm_log.append_event(
            production_year=production_year,
            event_type="RULE_ACTIVATION",
            actor_id="SYSTEM_PIPELINE",
            role="SYSTEM",
            manifest_sha256=calculated_rules_digest,
            metadata={"manifest_id": manifest_id, "source_sha256": source_document_sha256},
        )

        # 7. Kuralları VERIFIED Olarak Yükselt
        self.rule_repo.update_rule_status(production_year, "VERIFIED")

        # 8. Manifestoyu Kaydet
        manifest = ActivationManifest(
            manifest_id=manifest_id,
            production_year=production_year,
            source_document_sha256=source_document_sha256,
            rules_digest=calculated_rules_digest,
            rule_count=len(rules),
            status="ACTIVE",
            activated_at=now_utc,
            reviewer_attestation=reviewer_attestation,
            approver_attestation=approver_attestation,
            worm_block_sha256=act_block.block_sha256,
        )
        self.save_manifest(manifest)

        return manifest

    def revoke_activation(
        self,
        *,
        production_year: int,
        actor_id: str,
        reason: str,
        signature_b64: str | None = None,
    ) -> bool:
        """Belirtilen yılın yürürlük aktivasyonunu iptal eder (Fail-Closed: VERIFIED -> REVOKED)."""
        self.worm_log.verify_chain()

        manifest = self.get_manifest(production_year)
        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Kuralları REVOKED yap
        updated_count = self.rule_repo.update_rule_status(production_year, "REVOKED")

        # Manifestoyu güncelle
        if manifest is not None:
            updated_manifest = ActivationManifest(
                manifest_id=manifest.manifest_id,
                production_year=manifest.production_year,
                source_document_sha256=manifest.source_document_sha256,
                rules_digest=manifest.rules_digest,
                rule_count=manifest.rule_count,
                status="REVOKED",
                activated_at=manifest.activated_at,
                reviewer_attestation=manifest.reviewer_attestation,
                approver_attestation=manifest.approver_attestation,
                worm_block_sha256=manifest.worm_block_sha256,
                revocation_info={
                    "revoked_at": now_utc,
                    "revoked_by": actor_id,
                    "reason": reason,
                    "signature_b64": signature_b64,
                },
            )
            self.save_manifest(updated_manifest)

        # WORM kütüğüne ekle
        self.worm_log.append_event(
            production_year=production_year,
            event_type="RULE_REVOCATION",
            actor_id=actor_id,
            role="ADMIN",
            manifest_sha256=manifest.rules_digest if manifest else ("0" * 64),
            signature_b64=signature_b64,
            metadata={"reason": reason, "revoked_rules_count": updated_count},
        )

        return True

    def get_activation_status(self, production_year: int) -> dict[str, Any]:
        """Aktivasyon durumu, manifesto bilgisi ve WORM zincir durumunu özetler."""
        manifest = self.get_manifest(production_year)
        counts = self.rule_repo.get_status_counts(production_year)
        chain_ok, chain_msg = self.worm_log.verify_chain()

        status_label = "NOT_ACTIVATED"
        if manifest:
            status_label = manifest.status

        return {
            "production_year": production_year,
            "activation_status": status_label,
            "manifest": manifest.to_dict() if manifest else None,
            "rules_counts": counts,
            "worm_chain_verified": chain_ok,
            "worm_chain_message": chain_msg,
        }
