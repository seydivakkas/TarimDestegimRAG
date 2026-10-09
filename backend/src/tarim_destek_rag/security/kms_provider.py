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

"""Kurumsal Anahtar Yönetim Servisi ve Donanımsal Güvenlik Modülü (HSM/KMS) Sağlayıcısı (P0-13).

Bu modül, yasal onay ve yayın imzalarının doğrudan sunucu belleklerinde veya dosya
sistemlerinde açık metin (plaintext) olarak saklanmasını engeller.
Ed25519 asimetrik anahtarlarının HashiCorp Vault, Bulut KMS veya PKCS#11 uyumlu
Donanımsal Güvenlik Modülleri (HSM) arkasında soyutlanarak yönetilmesini sağlar.
"""

from __future__ import annotations

import abc
import base64
import binascii
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass(frozen=True)
class KmsKeyMetadata:
    """KMS/HSM tarafından yönetilen anahtara ait meta veriler."""

    key_id: str
    alias: str
    role: str = "ADMIN"  # "LEGAL_REVIEWER", "LEGAL_APPROVER", "RELEASE_SIGNER", "ADMIN"
    algorithm: str = "Ed25519"
    public_key_b64: str = ""
    enabled: bool = True
    created_at: str = ""
    hardware_backed: bool = False

    @property
    def created_at_utc(self) -> str:
        return self.created_at

    @property
    def is_enabled(self) -> bool:
        return self.enabled

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KeyManagementProvider(abc.ABC):
    """HSM ve Bulut KMS sağlayıcıları için temel soyut sınıf."""

    @abc.abstractmethod
    def list_keys(self) -> list[KmsKeyMetadata]:
        """KMS deposundaki kayıtlı anahtarları listeler."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_key(self, key_id_or_alias: str) -> KmsKeyMetadata | None:
        """Belirtilen anahtar kimliği veya takma adı ile anahtar meta verisini döner."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_public_key(self, key_id_or_alias: str) -> str:
        """Anahtarın base64 kodlu genel (public) anahtarını döner."""
        raise NotImplementedError

    @abc.abstractmethod
    def sign_payload(self, key_id_or_alias: str, payload_bytes: bytes) -> str:
        """KMS içinde korunan özel anahtar ile veriyi imzalar; imzayı hex döner."""
        raise NotImplementedError

    @abc.abstractmethod
    def verify_signature(
        self,
        key_id_or_alias: str,
        payload_bytes: bytes,
        signature: str,
    ) -> bool:
        """Verilen imzanın (hex veya base64) ilgili anahtar tarafından atıldığını doğrular."""
        raise NotImplementedError

    @abc.abstractmethod
    def health_check(self) -> dict[str, Any]:
        """KMS/HSM bağlantısının ve anahtar servisinin durumunu denetler."""
        raise NotImplementedError


class SoftwareKmsProvider(KeyManagementProvider):
    """Yerel geliştirme, CI/CD ve test ortamları için bellek içi Ed25519 yazılımsal KMS sağlayıcısı."""

    def __init__(self, predefined_keys: dict[str, dict[str, str]] | None = None) -> None:
        self._keys: dict[str, KmsKeyMetadata] = {}
        self._private_keys: dict[str, Ed25519PrivateKey] = {}
        self._init_keys(predefined_keys)

    def _init_keys(self, predefined: dict[str, dict[str, str]] | None = None) -> None:
        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Tanımlı roller ve anahtar takma adları
        default_roles = [
            ("key-reviewer-01", "legal-reviewer", "LEGAL_REVIEWER"),
            ("key-reviewer-alias", "legal-reviewer-primary", "LEGAL_REVIEWER"),
            ("key-approver-01", "legal-approver", "LEGAL_APPROVER"),
            ("key-approver-alias", "legal-approver-primary", "LEGAL_APPROVER"),
            ("key-release-01", "release-master", "RELEASE_SIGNER"),
            ("key-release-alias", "release-signer-primary", "RELEASE_SIGNER"),
            ("key-admin-01", "security-admin-primary", "ADMIN"),
        ]

        if predefined:
            for alias, info in predefined.items():
                role = info.get("role", "LEGAL_REVIEWER")
                priv_b64 = info.get("private_key_b64")
                if priv_b64:
                    raw_priv = base64.b64decode(priv_b64.encode("ascii"))
                    priv = Ed25519PrivateKey.from_private_bytes(raw_priv)
                else:
                    priv = Ed25519PrivateKey.generate()
                pub = priv.public_key()
                pub_b64 = base64.b64encode(pub.public_bytes_raw()).decode("ascii")

                meta = KmsKeyMetadata(
                    key_id=f"kms-{alias}",
                    alias=alias,
                    role=role,
                    algorithm="Ed25519",
                    public_key_b64=pub_b64,
                    enabled=True,
                    created_at=now_utc,
                    hardware_backed=False,
                )
                self._keys[meta.key_id] = meta
                self._keys[meta.alias] = meta
                self._private_keys[meta.key_id] = priv
                self._private_keys[meta.alias] = priv
            return

        for k_id, alias, role in default_roles:
            priv = Ed25519PrivateKey.generate()
            pub = priv.public_key()
            pub_b64 = base64.b64encode(pub.public_bytes_raw()).decode("ascii")

            meta = KmsKeyMetadata(
                key_id=k_id,
                alias=alias,
                role=role,
                algorithm="Ed25519",
                public_key_b64=pub_b64,
                enabled=True,
                created_at=now_utc,
                hardware_backed=False,
            )
            self._keys[k_id] = meta
            self._keys[alias] = meta
            self._private_keys[k_id] = priv
            self._private_keys[alias] = priv

    def generate_key(self, alias: str, role: str = "ADMIN", algorithm: str = "Ed25519") -> KmsKeyMetadata:
        """Yeni bir anahtar çifti üretip depoya kaydeder."""
        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        k_id = f"kms-{alias}"
        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key()
        pub_b64 = base64.b64encode(pub.public_bytes_raw()).decode("ascii")
        meta = KmsKeyMetadata(
            key_id=k_id,
            alias=alias,
            role=role,
            algorithm=algorithm,
            public_key_b64=pub_b64,
            enabled=True,
            created_at=now_utc,
            hardware_backed=False,
        )
        self._keys[k_id] = meta
        self._keys[alias] = meta
        self._private_keys[k_id] = priv
        self._private_keys[alias] = priv
        return meta

    def list_keys(self) -> list[KmsKeyMetadata]:
        unique: dict[str, KmsKeyMetadata] = {}
        for m in self._keys.values():
            unique[m.key_id] = m
        return list(unique.values())

    def get_key(self, key_id_or_alias: str) -> KmsKeyMetadata | None:
        return self._keys.get(key_id_or_alias)

    def get_public_key(self, key_id_or_alias: str) -> str:
        meta = self.get_key(key_id_or_alias)
        if meta is None or not meta.enabled:
            raise KeyError(f"KMS key not found in KMS or disabled: {key_id_or_alias}")
        return meta.public_key_b64

    def sign_payload(self, key_id_or_alias: str, payload_bytes: bytes) -> str:
        meta = self.get_key(key_id_or_alias)
        if meta is None or not meta.enabled:
            raise KeyError(f"KMS key '{key_id_or_alias}' not found in KMS")
        priv = self._private_keys.get(key_id_or_alias)
        if priv is None:
            raise KeyError(f"Private key for '{key_id_or_alias}' not found in KMS")
        sig = priv.sign(payload_bytes)
        return sig.hex()

    def verify_signature(
        self,
        key_id_or_alias: str,
        payload_bytes: bytes,
        signature: str,
    ) -> bool:
        meta = self.get_key(key_id_or_alias)
        if meta is None or not meta.enabled:
            return False
        try:
            pub_raw = base64.b64decode(meta.public_key_b64.encode("ascii"))
            if len(signature) == 128:
                try:
                    sig_raw = bytes.fromhex(signature)
                except ValueError:
                    sig_raw = base64.b64decode(signature.encode("ascii"))
            else:
                sig_raw = base64.b64decode(signature.encode("ascii"))

            if len(pub_raw) != 32 or len(sig_raw) != 64:
                return False
            pub = Ed25519PublicKey.from_public_bytes(pub_raw)
            pub.verify(sig_raw, payload_bytes)
            return True
        except (InvalidSignature, binascii.Error, ValueError):
            return False

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "HEALTHY",
            "provider": "SoftwareKmsProvider",
            "managed_keys_count": len(self.list_keys()),
            "isolation_level": "PROCESS_MEMORY",
        }


class HashiCorpVaultProvider(KeyManagementProvider):
    """Vault Transit interface. No software signing fallback is permissible."""

    def __init__(
        self,
        vault_url: str | None = None,
        vault_addr: str | None = None,
        token: str | None = None,
        vault_token: str | None = None,
        fallback_software: KeyManagementProvider | None = None,
    ) -> None:
        self.vault_addr = vault_url or vault_addr or os.getenv("VAULT_ADDR", "")
        self.vault_token = token or vault_token or os.getenv("VAULT_TOKEN", "")
        # Legacy constructor argument intentionally ignored. Never silently
        # substitute an in-process key for unavailable trusted hardware.
        self._connection_configured = bool(
            self.vault_addr.startswith("https://") and self.vault_token
        )

    def _vault_request(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        raise RuntimeError("Vault Transit network adapter is unavailable; no software fallback")

    def list_keys(self) -> list[KmsKeyMetadata]:
        return []

    def get_key(self, key_id_or_alias: str) -> KmsKeyMetadata | None:
        return None

    def get_public_key(self, key_id_or_alias: str) -> str:
        raise RuntimeError("Vault Transit key resolution has not been implemented")

    def sign_payload(self, key_id_or_alias: str, payload_bytes: bytes) -> str:
        if not self._connection_configured:
            raise RuntimeError("Vault Transit HTTPS endpoint and token are mandatory")
        b64_input = base64.b64encode(payload_bytes).decode("ascii")
        resp = self._vault_request(
            f"/v1/transit/sign/{key_id_or_alias}", {"input": b64_input}
        )
        sig_str = resp.get("signature", "")
        if isinstance(sig_str, str) and sig_str.startswith("vault:v1:"):
            try:
                raw = base64.b64decode(sig_str.split(":", 2)[-1], validate=True)
            except (ValueError, binascii.Error) as exc:
                raise RuntimeError("Vault Transit returned invalid signature") from exc
            if len(raw) == 64:
                return raw.hex()
        raise RuntimeError("Vault Transit signing unavailable or returned invalid Ed25519 signature")

    def verify_signature(
        self, key_id_or_alias: str, payload_bytes: bytes, signature: str
    ) -> bool:
        # Until a real Vault public-key registry and versioning are integrated,
        # no unverifiable external signature is accepted as trusted.
        return False

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "UNAVAILABLE",
            "provider": "HashiCorpVaultProvider",
            "vault_addr": self.vault_addr,
            "transit_engine_active": False,
            "managed_keys_count": 0,
        }


class PKCS11HsmProvider(KeyManagementProvider):
    """PKCS#11 adapter placeholder; never misrepresent software as hardware."""

    def __init__(
        self,
        slot_id: int = 0,
        pin: str | None = None,
        module_path: str | None = None,
        fallback_software: KeyManagementProvider | None = None,
    ) -> None:
        self.slot_id = slot_id
        self.pin = pin or os.getenv("HSM_PKCS11_PIN", "")
        self.module_path = module_path

    def list_keys(self) -> list[KmsKeyMetadata]:
        return []

    def get_key(self, key_id_or_alias: str) -> KmsKeyMetadata | None:
        return None

    def get_public_key(self, key_id_or_alias: str) -> str:
        raise RuntimeError("PKCS#11 key lookup is not connected")

    def sign_payload(self, key_id_or_alias: str, payload_bytes: bytes) -> str:
        if not self.module_path or not Path(self.module_path).exists():
            raise RuntimeError("HSM PKCS11 library not present or not configured")
        raise RuntimeError("HSM PKCS11 signing requires a verified hardware adapter")

    def verify_signature(
        self, key_id_or_alias: str, payload_bytes: bytes, signature: str
    ) -> bool:
        return False

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "UNAVAILABLE",
            "provider": "PKCS11HsmProvider",
            "slot_id": self.slot_id,
            "hardware_token_present": False,
            "managed_keys_count": 0,
        }


# Singleton KMS sağlayıcı örneği
_GLOBAL_KMS_PROVIDER: KeyManagementProvider | None = None


def get_kms_provider(provider_type: str | None = None) -> KeyManagementProvider:
    """Konfigürasyona uygun KMS/HSM sağlayıcısını döner (Fabrika Fonksiyonu)."""
    global _GLOBAL_KMS_PROVIDER
    if _GLOBAL_KMS_PROVIDER is not None and provider_type is None:
        return _GLOBAL_KMS_PROVIDER

    p_type = provider_type or os.getenv("TARIM_RAG_KMS_PROVIDER", "software").lower()

    if p_type in ("vault", "hashicorp"):
        provider = HashiCorpVaultProvider()
    elif p_type in ("hsm", "pkcs11"):
        provider = PKCS11HsmProvider()
    else:
        if os.getenv("TARIM_RAG_LEGAL_SECURITY_PROFILE") == "production":
            raise RuntimeError("Software KMS is forbidden for production legal signing")
        provider = SoftwareKmsProvider()

    if provider_type is None:
        _GLOBAL_KMS_PROVIDER = provider
    return provider


def set_global_kms_provider(provider: KeyManagementProvider | None) -> None:
    """Test veya ortam değiştirme amacıyla global KMS sağlayıcısını günceller."""
    global _GLOBAL_KMS_PROVIDER
    _GLOBAL_KMS_PROVIDER = provider
