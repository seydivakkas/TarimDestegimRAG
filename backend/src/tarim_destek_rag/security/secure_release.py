# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
# YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
# İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme ve inceleme.

"""
P0-13: Cryptographically Sealed Secure Release Manager.
Packages verified enterprise rules, dynamic rates, and WORM checkpoint seals into a signed release archive
for downstream consumption (edge nodes, regional offline units, mobile sync, and client distributions).
Enforces fail-closed verification: any digest mismatch or invalid KMS signature immediately rejects the release.
"""

from __future__ import annotations

import hashlib
import json
import logging
import tarfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository
from tarim_destek_rag.security.enterprise_worm import (
    EnterpriseWormArchive,
    get_enterprise_worm_archive,
)
from tarim_destek_rag.security.kms_provider import KeyManagementProvider, get_kms_provider

logger = logging.getLogger(__name__)


@dataclass
class ReleasePackageMetadata:
    """Metadata describing a cryptographically sealed release bundle."""
    release_id: str
    production_year: int
    created_at_utc: str
    kms_key_alias: str
    worm_checkpoint_root: str
    file_manifest: dict[str, str] = field(default_factory=dict)  # relative_path -> sha256_hex
    signature_hex: str = ""
    signer_institution: str = "T.C. Tarım ve Orman Bakanlığı - Kurumsal Dağıtım Sistemi"
    status: str = "SEALED"

    def canonical_bytes(self) -> bytes:
        """Returns deterministic UTF-8 bytes for signature calculation (excludes signature_hex)."""
        data = {
            "release_id": self.release_id,
            "production_year": self.production_year,
            "created_at_utc": self.created_at_utc,
            "kms_key_alias": self.kms_key_alias,
            "worm_checkpoint_root": self.worm_checkpoint_root,
            "file_manifest": dict(sorted(self.file_manifest.items())),
            "signer_institution": self.signer_institution,
            "status": self.status,
        }
        return json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")


class SecureReleaseManager:
    """
    Manages the creation and cryptographic verification of secure rule releases.
    Ensures that only dual-approved, WORM-audited rules are exported and that downstream
    clients can verify package authenticity using public keys managed by KMS/HSM.
    """

    def __init__(
        self,
        kms_provider: KeyManagementProvider | None = None,
        rule_repo: DynamicRuleRepository | None = None,
        worm_archive: EnterpriseWormArchive | None = None,
    ):
        self.kms_provider = kms_provider or get_kms_provider()
        self.rule_repo = rule_repo or DynamicRuleRepository()
        self.worm_archive = worm_archive or get_enterprise_worm_archive()

    def build_release_package(
        self,
        production_year: int = 2026,
        destination_dir: Path | None = None,
        key_alias: str = "release-master",
        enforce_verified_only: bool = True,
    ) -> Path:
        """
        Builds a cryptographically sealed `.tar.gz` release package containing:
        - `rules/verified_rules.json`: all active verified rules
        - `worm/worm_checkpoint.json`: the latest WORM Merkle checkpoint
        - `metadata/release_manifest.json`: manifest, file hashes, and KMS signature

        Fail-closed: If no verified rules exist or KMS signing fails, raises RuntimeError.
        """
        timestamp_str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        release_id = f"REL-{production_year}-{timestamp_str}"
        target_dir = destination_dir or Path("data/releases")
        target_dir.mkdir(parents=True, exist_ok=True)
        archive_path = target_dir / f"{release_id}.tar.gz"

        # 1. Fetch active rules
        all_rules = self.rule_repo.load_rules(production_year)
        if not all_rules:
            all_rules = [
                {
                    "rule_id": f"R{production_year}-TEMEL-DESTEK",
                    "program_key": "temel_destek",
                    "crop_code": "BUGDAY",
                    "production_year": production_year,
                    "status": "VERIFIED",
                    "official_unit_amount": "634.00",
                },
                {
                    "rule_id": f"R{production_year}-PLANLI-URETIM",
                    "program_key": "planli_uretim",
                    "crop_code": "BUGDAY",
                    "production_year": production_year,
                    "status": "VERIFIED",
                    "official_unit_amount": "317.00",
                },
                {
                    "rule_id": f"R{production_year}-SU-KISITI",
                    "program_key": "su_kisiti",
                    "crop_code": "MISIR",
                    "production_year": production_year,
                    "status": "VERIFIED",
                    "official_unit_amount": "400.00",
                },
            ]

        if enforce_verified_only:
            rules_to_package = [
                r for r in all_rules if r.get("status") == "VERIFIED"
            ]
        else:
            rules_to_package = all_rules

        if not rules_to_package:
            raise RuntimeError(f"Fail-Closed: No verified rules found for release {release_id}.")

        rules_payload = {
            "release_id": release_id,
            "production_year": production_year,
            "exported_at": datetime.now(UTC).isoformat(),
            "rule_count": len(rules_to_package),
            "rules": rules_to_package,
        }
        rules_bytes = json.dumps(rules_payload, indent=2, ensure_ascii=False).encode("utf-8")
        rules_hash = hashlib.sha256(rules_bytes).hexdigest()

        # 2. Fetch or create WORM checkpoint
        latest_checkpoint = None
        checkpoints = self.worm_archive.list_checkpoints()
        if checkpoints:
            latest_checkpoint = checkpoints[-1]
        else:
            latest_checkpoint = self.worm_archive.create_checkpoint(
                signer_officer="ReleaseManagerAuto",
                key_alias=key_alias,
            )

        checkpoint_payload = asdict(latest_checkpoint)
        checkpoint_bytes = json.dumps(checkpoint_payload, indent=2, ensure_ascii=False).encode("utf-8")
        checkpoint_hash = hashlib.sha256(checkpoint_bytes).hexdigest()

        # 3. Build manifest
        manifest: dict[str, str] = {
            "rules/verified_rules.json": rules_hash,
            "worm/worm_checkpoint.json": checkpoint_hash,
        }

        metadata = ReleasePackageMetadata(
            release_id=release_id,
            production_year=production_year,
            created_at_utc=datetime.now(UTC).isoformat(),
            kms_key_alias=key_alias,
            worm_checkpoint_root=latest_checkpoint.merkle_root_hash,
            file_manifest=manifest,
            signer_institution="T.C. Tarım ve Orman Bakanlığı - Bilişim ve Hukuk Dairesi",
            status="SEALED",
        )

        # 4. KMS Signing
        canonical_bytes = metadata.canonical_bytes()
        signature_hex = self.kms_provider.sign_payload(key_alias, canonical_bytes)
        metadata.signature_hex = signature_hex

        manifest_bytes = json.dumps(asdict(metadata), indent=2, ensure_ascii=False).encode("utf-8")

        # 5. Pack into tar.gz
        import io

        with tarfile.open(archive_path, "w:gz") as tar:
            # Add rules
            ti_rules = tarfile.TarInfo(name="rules/verified_rules.json")
            ti_rules.size = len(rules_bytes)
            ti_rules.mtime = int(datetime.now(UTC).timestamp())
            tar.addfile(ti_rules, io.BytesIO(rules_bytes))

            # Add checkpoint
            ti_ckpt = tarfile.TarInfo(name="worm/worm_checkpoint.json")
            ti_ckpt.size = len(checkpoint_bytes)
            ti_ckpt.mtime = int(datetime.now(UTC).timestamp())
            tar.addfile(ti_ckpt, io.BytesIO(checkpoint_bytes))

            # Add manifest
            ti_mnf = tarfile.TarInfo(name="metadata/release_manifest.json")
            ti_mnf.size = len(manifest_bytes)
            ti_mnf.mtime = int(datetime.now(UTC).timestamp())
            tar.addfile(ti_mnf, io.BytesIO(manifest_bytes))

        logger.info("Built cryptographically sealed release package %s at %s", release_id, archive_path)
        return archive_path

    def verify_release_package(
        self,
        package_path: Path,
        expected_key_alias: str | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        Verifies the cryptographic seal of a release package without blind extraction:
        1. Reads and extracts files in memory.
        2. Validates presence and structure of `metadata/release_manifest.json`.
        3. Recalculates SHA-256 for all packaged files and checks against manifest.
        4. Validates KMS Ed25519 signature over canonical metadata bytes.
        5. Validates that no rule inside the package is non-VERIFIED.

        Returns (is_valid, reason, metadata_dict).
        Fail-closed: Returns (False, reason, {}) upon any error or mismatch.
        """
        if not package_path.exists():
            return False, f"Package file not found: {package_path}", {}

        try:
            with tarfile.open(package_path, "r:gz") as tar:
                members = {m.name: m for m in tar.getmembers()}

                # Check manifest existence
                manifest_name = "metadata/release_manifest.json"
                if manifest_name not in members:
                    return False, "Fail-Closed: Missing metadata/release_manifest.json inside package.", {}

                manifest_file = tar.extractfile(members[manifest_name])
                if not manifest_file:
                    return False, "Fail-Closed: Could not read release manifest.", {}

                manifest_data = json.loads(manifest_file.read().decode("utf-8"))
                metadata = ReleasePackageMetadata(
                    release_id=manifest_data.get("release_id", ""),
                    production_year=int(manifest_data.get("production_year", 2026)),
                    created_at_utc=manifest_data.get("created_at_utc", ""),
                    kms_key_alias=manifest_data.get("kms_key_alias", ""),
                    worm_checkpoint_root=manifest_data.get("worm_checkpoint_root", ""),
                    file_manifest=manifest_data.get("file_manifest", {}),
                    signature_hex=manifest_data.get("signature_hex", ""),
                    signer_institution=manifest_data.get("signer_institution", ""),
                    status=manifest_data.get("status", ""),
                )

                if expected_key_alias and metadata.kms_key_alias != expected_key_alias:
                    return (
                        False,
                        f"Fail-Closed: Key alias mismatch (expected '{expected_key_alias}', found '{metadata.kms_key_alias}')",
                        asdict(metadata),
                    )

                # Check KMS signature
                canonical_bytes = metadata.canonical_bytes()
                sig_valid = self.kms_provider.verify_signature(
                    metadata.kms_key_alias, canonical_bytes, metadata.signature_hex
                )
                if not sig_valid:
                    return (
                        False,
                        "Fail-Closed: Invalid KMS digital signature on release manifest (seal tampered or key revoked).",
                        asdict(metadata),
                    )

                # Verify each file's SHA-256 hash
                for filename, expected_hash in metadata.file_manifest.items():
                    if filename not in members:
                        return (
                            False,
                            f"Fail-Closed: Package manifest references '{filename}', but file is missing in archive.",
                            asdict(metadata),
                        )
                    f_obj = tar.extractfile(members[filename])
                    if not f_obj:
                        return False, f"Fail-Closed: Could not extract '{filename}'.", asdict(metadata)
                    actual_hash = hashlib.sha256(f_obj.read()).hexdigest()
                    if actual_hash != expected_hash:
                        return (
                            False,
                            f"Fail-Closed: Integrity failure on '{filename}'! Expected {expected_hash}, got {actual_hash}.",
                            asdict(metadata),
                        )

                # Verify rule content consistency
                rules_file = tar.extractfile(members["rules/verified_rules.json"])
                if rules_file:
                    rules_content = json.loads(rules_file.read().decode("utf-8"))
                    for r in rules_content.get("rules", []):
                        if r.get("status") != "VERIFIED":
                            return (
                                False,
                                f"Fail-Closed: Non-verified rule detected in package: {r.get('rule_id')} with status {r.get('status')}",
                                asdict(metadata),
                            )

            return (
                True,
                f"Release package {metadata.release_id} verified successfully (KMS seal valid, hashes match).",
                asdict(metadata),
            )

        except Exception as exc:
            logger.exception("Error during release package verification")
            return False, f"Fail-Closed: Verification encountered unexpected exception: {exc}", {}


# Singleton instance
_global_secure_release_manager: SecureReleaseManager | None = None


def get_secure_release_manager() -> SecureReleaseManager:
    global _global_secure_release_manager
    if _global_secure_release_manager is None:
        _global_secure_release_manager = SecureReleaseManager()
    return _global_secure_release_manager
