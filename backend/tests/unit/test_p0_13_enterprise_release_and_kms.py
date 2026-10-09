# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
# YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
# İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme ve inceleme.

"""
P0-13 Unit Test Suite:
Comprehensive verification of enterprise KMS/HSM abstraction,
PostgreSQL role/RLS audit, WORM checkpoints & court-admissible evidence vaults,
enterprise revocation taxonomy, and tamper-proof secure releases.
"""

from __future__ import annotations

import io
import json
import os
import tarfile
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app
from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository
from tarim_destek_rag.security.database_roles import (
    get_database_role_manager,
)
from tarim_destek_rag.security.enterprise_worm import (
    EnterpriseWormArchive,
)
from tarim_destek_rag.security.kms_provider import (
    HashiCorpVaultProvider,
    PKCS11HsmProvider,
    SoftwareKmsProvider,
    get_kms_provider,
    set_global_kms_provider,
)
from tarim_destek_rag.security.revocation_manager import (
    REVOCATION_REASON_TAXONOMY,
    EnterpriseRevocationManager,
    get_enterprise_revocation_manager,
)
from tarim_destek_rag.security.secure_release import (
    SecureReleaseManager,
)

# ---------------------------------------------------------------------------
# 1. KMS / HSM Abstraction Tests
# ---------------------------------------------------------------------------

class TestKmsProvider:
    def test_software_kms_generate_and_list_keys(self):
        kms = SoftwareKmsProvider()
        meta = kms.generate_key("test-alias")
        assert meta.alias == "test-alias"
        assert meta.algorithm == "Ed25519"
        assert meta.is_enabled is True
        assert meta.hardware_backed is False

        keys = kms.list_keys()
        aliases = [k.alias for k in keys]
        assert "test-alias" in aliases

    def test_software_kms_sign_and_verify(self):
        kms = SoftwareKmsProvider()
        kms.generate_key("signer-key")
        payload = b"Hukuki Kararname 2026 Test Metni"

        sig_hex = kms.sign_payload("signer-key", payload)
        assert len(sig_hex) == 128  # 64 bytes Ed25519 in hex

        # Valid signature
        assert kms.verify_signature("signer-key", payload, sig_hex) is True

        # Tampered payload -> fail-closed
        assert kms.verify_signature("signer-key", b"Tampered Metin", sig_hex) is False

        # Tampered signature -> fail-closed
        tampered_sig = ("0" if sig_hex[0] != "0" else "1") + sig_hex[1:]
        assert kms.verify_signature("signer-key", payload, tampered_sig) is False

    def test_kms_fail_closed_on_unknown_key(self):
        kms = SoftwareKmsProvider()
        with pytest.raises(KeyError, match="not found in KMS"):
            kms.sign_payload("non-existent-alias", b"data")

        assert kms.verify_signature("non-existent-alias", b"data", "abcd") is False

    def test_hashicorp_vault_mock_signing(self):
        vault = HashiCorpVaultProvider(vault_url="https://vault.internal:8200", token="test-token")
        import base64
        fake_sig = "vault:v1:" + base64.b64encode(b"X" * 64).decode("ascii")

        with patch.object(vault, "_vault_request", return_value={"signature": fake_sig}):
            sig = vault.sign_payload("prod-transit-key", b"hello vault")
            assert sig == (b"X" * 64).hex()

    def test_pkcs11_hsm_unsupported_graceful_fail_closed(self):
        hsm = PKCS11HsmProvider(slot_id=1, pin="1234", module_path="/non/existent/libpkcs11.so")
        with pytest.raises(RuntimeError, match="HSM|PKCS11|library"):
            hsm.sign_payload("hsm-token", b"test")

    def test_global_kms_provider_factory(self):
        kms = get_kms_provider()
        assert kms is not None
        custom_kms = SoftwareKmsProvider()
        set_global_kms_provider(custom_kms)
        assert get_kms_provider() is custom_kms


# ---------------------------------------------------------------------------
# 2. Database Role & RLS Audit Tests
# ---------------------------------------------------------------------------

class TestDatabaseRoles:
    def test_database_role_manager_audit(self):
        manager = get_database_role_manager()
        report = manager.audit_roles()

        assert "database_dialect" in report
        assert "defined_roles" in report
        assert "script_path" in report
        assert report["script_available"] is True

        role_names = [r["role_name"] for r in report["defined_roles"]]
        assert "tarim_app_reader" in role_names
        assert "tarim_rule_editor" in role_names
        assert "tarim_legal_reviewer" in role_names
        assert "tarim_legal_approver" in role_names
        assert "tarim_worm_auditor" in role_names
        assert "tarim_admin" in role_names

    def test_permission_matrix_enforcement(self):
        manager = get_database_role_manager()

        # Reader cannot insert/update/delete
        assert manager.check_permission("tarim_app_reader", "support_amounts", "SELECT") is True
        assert manager.check_permission("tarim_app_reader", "support_amounts", "INSERT") is False
        assert manager.check_permission("tarim_app_reader", "support_amounts", "UPDATE") is False
        assert manager.check_permission("tarim_app_reader", "support_amounts", "DELETE") is False

        # WORM Auditor can inspect (SELECT) but CANNOT mutate or delete WORM log
        assert manager.check_permission("tarim_worm_auditor", "legal_approval_attestations", "SELECT") is True
        assert manager.check_permission("tarim_worm_auditor", "legal_approval_attestations", "UPDATE") is False
        assert manager.check_permission("tarim_worm_auditor", "legal_approval_attestations", "DELETE") is False

        # Unknown role / invalid operation fails closed
        assert manager.check_permission("unknown_role", "support_amounts", "SELECT") is False
        assert manager.check_permission("tarim_app_reader", "support_amounts", "DROP") is False

    def test_scoped_role_context_manager(self):
        manager = get_database_role_manager()
        mock_session = MagicMock()

        with manager.scoped_role(mock_session, "tarim_app_reader"):
            pass

        # Validates execute was called to set role
        assert mock_session.execute.called


# ---------------------------------------------------------------------------
# 3. Enterprise WORM & Legal Evidence Vault Tests
# ---------------------------------------------------------------------------

class TestEnterpriseWormAndEvidenceVault:
    def test_worm_checkpoint_creation_and_listing(self, tmp_path):
        archive = EnterpriseWormArchive(archive_dir=tmp_path / "worm")
        ckpt = archive.create_checkpoint(signer_officer="ChiefAuditor", key_alias="release-master")

        assert ckpt.checkpoint_id.startswith("CKPT-")
        assert len(ckpt.merkle_root_hash) == 64
        assert ckpt.signer_officer == "ChiefAuditor"
        assert len(ckpt.kms_signature_hex) == 128

        checkpoints = archive.list_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0].checkpoint_id == ckpt.checkpoint_id

    def test_export_legal_evidence_vault_zip(self, tmp_path):
        archive = EnterpriseWormArchive(archive_dir=tmp_path / "worm")
        zip_path = archive.export_legal_evidence_vault(
            production_year=2026,
            signer_officer="Dr. Legal Expert",
            key_alias="legal-approver",
            output_dir=tmp_path / "vaults",
        )

        assert zip_path.exists()
        assert zip_path.name.endswith(".zip")
        assert "EVIDENCE_VAULT_2026" in zip_path.name

        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            assert "verification_report.json" in names
            assert "sha256sums.txt" in names
            assert "evidence_package_seal.json" in names

            seal_data = json.loads(z.read("evidence_package_seal.json").decode("utf-8"))
            assert seal_data["production_year"] == 2026
            assert seal_data["signer_officer"] == "Dr. Legal Expert"
            assert seal_data["kms_key_alias"] == "legal-approver"
            assert "kms_signature_hex" in seal_data


# ---------------------------------------------------------------------------
# 4. Enterprise Revocation Manager Tests
# ---------------------------------------------------------------------------

class TestEnterpriseRevocationManager:
    def test_revocation_taxonomy_complete(self):
        manager = get_enterprise_revocation_manager()
        assert "COURT_STAY_OF_EXECUTION" in manager.reasons
        assert "REGULATION_AMENDED" in manager.reasons
        assert "BUDGET_EXHAUSTION" in manager.reasons
        assert "CLERICAL_ERROR" in manager.reasons
        assert "ADMINISTRATIVE_SUSPENSION" in manager.reasons

    def test_invalid_reason_code_fails_closed(self, tmp_path):
        manager = EnterpriseRevocationManager(
            certificates_dir=tmp_path / "certs",
            reasons=REVOCATION_REASON_TAXONOMY,
        )
        with pytest.raises(ValueError, match="Invalid revocation reason"):
            manager.revoke_rule(
                rule_id="R-TEST",
                reason_code="INVALID_REASON",
                legal_reference="Ref-123",
                authorized_officer="Auditor",
            )

    def test_successful_rule_revocation_and_certificate(self, tmp_path):
        manager = EnterpriseRevocationManager(
            certificates_dir=tmp_path / "certs",
            reasons=REVOCATION_REASON_TAXONOMY,
        )

        cert = manager.revoke_rule(
            rule_id="R2026-FARM-TEST-001",
            reason_code="COURT_STAY_OF_EXECUTION",
            legal_reference="Danistay 10. Daire 2026/1042 E.",
            authorized_officer="Bakanlik Bas Hukuk Musaviri",
            notes="Yurutmenin durdurulmasi karari uyarinca acil iptal.",
            key_alias="legal-approver",
        )

        assert cert.certificate_id.startswith("REV-")
        assert cert.rule_id == "R2026-FARM-TEST-001"
        assert cert.reason_code == "COURT_STAY_OF_EXECUTION"
        assert len(cert.kms_signature_hex) == 128

        # Cert file was written to disk
        cert_file = tmp_path / "certs" / f"{cert.certificate_id}.json"
        assert cert_file.exists()
        loaded_data = json.loads(cert_file.read_text(encoding="utf-8"))
        assert loaded_data["certificate_id"] == cert.certificate_id


# ---------------------------------------------------------------------------
# 5. Secure Release Packaging & Verification Tests
# ---------------------------------------------------------------------------

class TestSecureReleaseManager:
    def test_build_and_verify_release_package(self, tmp_path):
        kms = SoftwareKmsProvider()
        archive = EnterpriseWormArchive(archive_dir=tmp_path / "worm", kms_provider=kms)
        repo = DynamicRuleRepository(tmp_path / "rules_repo")
        repo.save_rules(
            2026,
            [
                {
                    "rule_id": "R2026-TEST-001",
                    "status": "VERIFIED",
                    "program_key": "temel_destek",
                    "crop_code": "BUGDAY",
                }
            ],
        )

        release_mgr = SecureReleaseManager(
            kms_provider=kms,
            rule_repo=repo,
            worm_archive=archive,
        )

        pkg_path = release_mgr.build_release_package(
            production_year=2026,
            destination_dir=tmp_path / "releases",
            key_alias="release-master",
            enforce_verified_only=True,
        )

        assert pkg_path.exists()
        assert pkg_path.name.endswith(".tar.gz")

        # Verify untouched package
        is_valid, reason, meta = release_mgr.verify_release_package(pkg_path, "release-master")
        assert is_valid is True
        assert "verified successfully" in reason.lower()
        assert meta["release_id"].startswith("REL-2026-")

    def test_verify_release_detects_tampered_file(self, tmp_path):
        kms = SoftwareKmsProvider()
        archive = EnterpriseWormArchive(archive_dir=tmp_path / "worm", kms_provider=kms)
        repo = DynamicRuleRepository(tmp_path / "rules_repo")
        repo.save_rules(
            2026,
            [
                {
                    "rule_id": "R2026-TEST-001",
                    "status": "VERIFIED",
                    "program_key": "temel_destek",
                    "crop_code": "BUGDAY",
                }
            ],
        )

        release_mgr = SecureReleaseManager(kms_provider=kms, rule_repo=repo, worm_archive=archive)
        pkg_path = release_mgr.build_release_package(
            production_year=2026,
            destination_dir=tmp_path / "releases",
            key_alias="release-master",
        )

        # Corrupt one file inside tar archive
        corrupted_path = tmp_path / "corrupted.tar.gz"
        with tarfile.open(pkg_path, "r:gz") as src_tar, tarfile.open(corrupted_path, "w:gz") as dst_tar:
            for member in src_tar.getmembers():
                f_obj = src_tar.extractfile(member)
                if f_obj is None:
                    continue
                content = f_obj.read()
                if member.name == "rules/verified_rules.json":
                    content = content + b"\n/* malicious modification */"
                ti = tarfile.TarInfo(name=member.name)
                ti.size = len(content)
                ti.mtime = member.mtime
                dst_tar.addfile(ti, io.BytesIO(content))

        # Verification must fail closed
        is_valid, reason, _ = release_mgr.verify_release_package(corrupted_path, "release-master")
        assert is_valid is False
        assert "integrity failure" in reason.lower() or "fail-closed" in reason.lower()

    def test_verify_release_key_alias_mismatch(self, tmp_path):
        kms = SoftwareKmsProvider()
        archive = EnterpriseWormArchive(archive_dir=tmp_path / "worm", kms_provider=kms)
        repo = DynamicRuleRepository(tmp_path / "rules_repo")
        repo.save_rules(
            2026,
            [
                {
                    "rule_id": "R2026-TEST-001",
                    "status": "VERIFIED",
                    "program_key": "temel_destek",
                    "crop_code": "BUGDAY",
                }
            ],
        )

        release_mgr = SecureReleaseManager(kms_provider=kms, rule_repo=repo, worm_archive=archive)
        pkg_path = release_mgr.build_release_package(
            production_year=2026,
            destination_dir=tmp_path / "releases",
            key_alias="release-master",
        )

        is_valid, reason, _ = release_mgr.verify_release_package(pkg_path, "different-key")
        assert is_valid is False
        assert "key alias mismatch" in reason.lower()



# ---------------------------------------------------------------------------
# 6. FastAPI Enterprise Endpoints Tests
# ---------------------------------------------------------------------------

class TestFastApiEnterpriseEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def admin_headers(self):
        admin_key = os.getenv("TARIM_RAG_ADMIN_API_KEY", "test-admin-secret-key-2026")
        os.environ["TARIM_RAG_ADMIN_API_KEY"] = admin_key
        return {"X-Admin-Key": admin_key}

    def test_get_kms_status_endpoint(self, client, admin_headers):
        res = client.get("/admin/enterprise/kms/status", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "provider_type" in data
        assert "key_count" in data
        assert "keys" in data
        assert isinstance(data["keys"], list)

    def test_audit_db_roles_endpoint(self, client, admin_headers):
        res = client.get("/admin/enterprise/db-roles/audit", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "database_dialect" in data
        assert "defined_roles" in data
        assert data["script_available"] is True

    def test_build_and_verify_release_endpoints(self, client, admin_headers):
        # 1. Build release
        build_payload = {
            "production_year": 2026,
            "key_alias": "release-master",
            "enforce_verified_only": False,  # Allow test suite existing rules
        }
        res_build = client.post("/admin/enterprise/release/build", json=build_payload, headers=admin_headers)
        assert res_build.status_code == 200
        b_data = res_build.json()
        assert b_data["status"] == "SEALED_SUCCESSFULLY"
        archive_path = b_data["archive_path"]

        # 2. Verify release
        verify_payload = {
            "package_path": archive_path,
            "expected_key_alias": "release-master",
        }
        res_verify = client.post("/admin/enterprise/release/verify", json=verify_payload, headers=admin_headers)
        assert res_verify.status_code == 200
        v_data = res_verify.json()
        assert v_data["status"] == "VERIFIED"

    def test_enterprise_revocation_endpoint(self, client, admin_headers):
        payload = {
            "rule_id": "R2026-TEST-API-001",
            "reason_code": "BUDGET_EXHAUSTION",
            "legal_reference": "Strateji ve Bütçe Başkanlığı Karar 2026/4",
            "authorized_officer": "Bütçe Dairesi Başkanı",
            "notes": "Tahsisat limiti tükendiği için yürürlük durduruldu.",
            "key_alias": "legal-approver",
        }
        res = client.post("/admin/enterprise/revoke/enterprise", json=payload, headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "REVOKED_SUCCESSFULLY"
        assert data["certificate"]["reason_code"] == "BUDGET_EXHAUSTION"

    def test_export_evidence_vault_endpoint(self, client, admin_headers):
        res = client.get("/admin/enterprise/evidence-vault/export?production_year=2026", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "EVIDENCE_VAULT_EXPORTED"
        assert "vault_path" in data
        assert data["vault_filename"].endswith(".zip")

    def test_unauthorized_access_denied(self, client):
        # Request without header fails with 401 or 403
        res = client.get("/admin/enterprise/kms/status")
        assert res.status_code in (401, 403)
