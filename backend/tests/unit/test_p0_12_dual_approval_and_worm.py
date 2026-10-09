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

"""P0-12 Çift Onaylı Hukuki İnceleme & WORM Aktivasyon Hattı Birim Testleri.

Kapsam:
  1. Ed25519 asimetrik anahtar üretimi ve imza doğrulama.
  2. Görevler Ayrılığı (Separation of Duties) kontrolleri.
  3. Kriptografik WORM denetim kütüğü hash zincirleme ve tahrifat algılama (Tamper Detection).
  4. Güvenilir anahtar deposu (Trusted Keystore) kontrolleri.
  5. DRAFT -> VERIFIED geçişi ve DynamicSupportEvaluator hak ediş kilit açma (total_payable_amount).
  6. Anlık fail-closed iptal (REVOKE) mekanizması.
  7. FastAPI admin uç noktaları entegrasyonu.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app
from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository
from tarim_destek_rag.rules.dynamic_support_evaluator import DynamicSupportEvaluator
from tarim_destek_rag.rules.legal_activation import (
    InvalidSignatureError,
    LegalAttestation,
    RuleActivationPipeline,
    SeparationOfDutiesViolation,
    TrustedKeyMismatchError,
    build_canonical_manifest_bytes,
    generate_ed25519_keypair,
    sign_payload_ed25519,
    verify_signature_ed25519,
)
from tarim_destek_rag.rules.worm_audit import (
    TamperedAuditError,
    WormAuditLog,
)


@pytest.fixture
def temp_archive(tmp_path: Path) -> Path:
    """İzole test için geçici mevzuat arşiv dizini."""
    archive_dir = tmp_path / "legal_update_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


@pytest.fixture
def sample_draft_rules(temp_archive: Path) -> list[dict]:
    """Test için 2026 yılı taslak (DRAFT) kuralları oluşturur ve kaydeder."""
    repo = DynamicRuleRepository(temp_archive)
    rules = [
        {
            "schema_version": 1,
            "rule_id": "DYN-2026-BASIC_SUPPORT-BUGDAY",
            "program_key": "BASIC_SUPPORT",
            "crop_code": "BUĞDAY",
            "production_year": 2026,
            "province": "*",
            "district": "*",
            "base_coefficient": "244.00",
            "category_multiplier": "1.00",
            "official_unit_amount": "244.00",
            "unit": "TRY/da",
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "published_at": "2025-11-01",
            "discovered_at": "2026-02-01",
            "source_document_sha256": "a" * 64,
            "source_sentence_id": 101,
            "conditions": {
                "all_of": [
                    {"field": "cks_registered", "op": "eq", "value": True},
                    {"field": "crop_code", "op": "eq", "value": "BUĞDAY"},
                ]
            },
            "review_status": "DRAFT",
        },
        {
            "schema_version": 1,
            "rule_id": "DYN-2026-PLANNED_PRODUCTION-BUGDAY",
            "program_key": "PLANNED_PRODUCTION",
            "crop_code": "BUĞDAY",
            "production_year": 2026,
            "province": "KONYA",
            "district": "*",
            "base_coefficient": "244.00",
            "category_multiplier": "1.00",
            "official_unit_amount": "244.00",
            "unit": "TRY/da",
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "published_at": "2025-11-01",
            "discovered_at": "2026-02-01",
            "source_document_sha256": "a" * 64,
            "source_sentence_id": 102,
            "conditions": {
                "all_of": [
                    {"field": "cks_registered", "op": "eq", "value": True},
                    {"field": "crop_code", "op": "eq", "value": "BUĞDAY"},
                ]
            },
            "review_status": "DRAFT",
        },
    ]
    repo.save_rules(2026, rules)
    return rules


# ---------------------------------------------------------------------------
# 1. Kriptografik İmza ve Anahtar Testleri
# ---------------------------------------------------------------------------

def test_ed25519_keypair_and_sign_verify():
    """Ed25519 anahtar çifti üretimi ve imza doğrulamasını test eder."""
    priv_b64, pub_b64 = generate_ed25519_keypair()
    assert len(priv_b64) > 0
    assert len(pub_b64) > 0

    payload = b'{"action":"test_approval","year":2026}'
    signature = sign_payload_ed25519(priv_b64, payload)
    assert len(signature) > 0

    # Doğru imza
    assert verify_signature_ed25519(pub_b64, signature, payload) is True

    # Değiştirilmiş yük
    tampered_payload = b'{"action":"test_approval","year":2027}'
    assert verify_signature_ed25519(pub_b64, signature, tampered_payload) is False

    # Farklı genel anahtar
    _, other_pub = generate_ed25519_keypair()
    assert verify_signature_ed25519(other_pub, signature, payload) is False


# ---------------------------------------------------------------------------
# 2. WORM Denetim Kütüğü ve Zincir Bütünlüğü
# ---------------------------------------------------------------------------

def test_worm_genesis_and_chain_append(temp_archive: Path):
    """WORM başlangıç (Genesis) bloğu ve sıralı blok eklemeyi test eder."""
    worm = WormAuditLog(temp_archive)
    blocks = worm.load_blocks()
    assert len(blocks) == 1
    assert blocks[0].block_index == 0
    assert blocks[0].event_type == "GENESIS"
    assert blocks[0].previous_block_sha256 == "0" * 64

    # Zinciri doğrula
    ok, msg = worm.verify_chain()
    assert ok is True

    # Yeni olay ekle
    b1 = worm.append_event(
        production_year=2026,
        event_type="ATTESTATION_REVIEW",
        actor_id="REV_01",
        role="LEGAL_REVIEWER",
        manifest_sha256="m" * 64,
        metadata={"note": "first review"},
    )
    assert b1.block_index == 1
    assert b1.previous_block_sha256 == blocks[0].block_sha256

    b2 = worm.append_event(
        production_year=2026,
        event_type="RULE_ACTIVATION",
        actor_id="SYS",
        role="SYSTEM",
        manifest_sha256="m" * 64,
    )
    assert b2.block_index == 2
    assert b2.previous_block_sha256 == b1.block_sha256

    ok, msg = worm.verify_chain()
    assert ok is True
    assert "3 blok" in msg


def test_worm_tamper_detection(temp_archive: Path):
    """WORM dosyasında yapılan tahrifatın fail-closed olarak yakalandığını test eder."""
    worm = WormAuditLog(temp_archive)
    worm.append_event(
        production_year=2026,
        event_type="ATTESTATION_REVIEW",
        actor_id="REV_01",
        role="LEGAL_REVIEWER",
        manifest_sha256="m" * 64,
    )

    log_path = temp_archive / "worm_audit" / "audit_chain.jsonl"
    lines = log_path.read_text(encoding="utf-8").splitlines()

    # İkinci bloğun aktör bilgisini manipüle et
    data = json.loads(lines[1])
    data["actor_id"] = "MALICIOUS_ACTOR"
    lines[1] = json.dumps(data)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # verify_chain TamperedAuditError fırlatmalı
    with pytest.raises(TamperedAuditError) as exc_info:
        worm.verify_chain()
    assert "manipüle edilmiş" in str(exc_info.value) or "manipülasyonu" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Görevler Ayrılığı (Separation of Duties)
# ---------------------------------------------------------------------------

def test_separation_of_duties_same_actor_rejected(temp_archive: Path, sample_draft_rules: list[dict]):
    """İnceleyen ve onaylayan aynı kişi olduğunda aktivasyonun reddedildiğini test eder."""
    pipeline = RuleActivationPipeline(temp_archive)
    repo = DynamicRuleRepository(temp_archive)
    digest = repo.compute_rules_digest(2026)

    priv1, pub1 = generate_ed25519_keypair()
    priv2, pub2 = generate_ed25519_keypair()

    statement = "2026 kuralları incelendi ve onaylandı."
    canon_bytes = build_canonical_manifest_bytes(
        production_year=2026,
        source_document_sha256="a" * 64,
        rules_digest=digest,
        rule_count=len(sample_draft_rules),
        statement=statement,
    )

    sig1 = sign_payload_ed25519(priv1, canon_bytes)
    sig2 = sign_payload_ed25519(priv2, canon_bytes)

    # Aynı actor_id
    att_rev = LegalAttestation(
        actor_id="SAME_OFFICER",
        role="LEGAL_REVIEWER",
        public_key_b64=pub1,
        signature_b64=sig1,
        signed_at="2026-02-01T10:00:00Z",
        statement=statement,
    )
    att_app = LegalAttestation(
        actor_id="SAME_OFFICER",
        role="LEGAL_APPROVER",
        public_key_b64=pub2,
        signature_b64=sig2,
        signed_at="2026-02-01T10:05:00Z",
        statement=statement,
    )

    with pytest.raises(SeparationOfDutiesViolation) as exc:
        pipeline.activate_rules(
            production_year=2026,
            reviewer_attestation=att_rev,
            approver_attestation=att_app,
            source_document_sha256="a" * 64,
        )
    assert "aynı aktör olamaz" in str(exc.value)


def test_separation_of_duties_same_key_rejected(temp_archive: Path, sample_draft_rules: list[dict]):
    """İnceleyen ve onaylayan farklı aktör ama aynı anahtarı kullandığında reddedildiğini test eder."""
    pipeline = RuleActivationPipeline(temp_archive)
    repo = DynamicRuleRepository(temp_archive)
    digest = repo.compute_rules_digest(2026)

    priv, pub = generate_ed25519_keypair()
    statement = "2026 kuralları incelendi ve onaylandı."
    canon_bytes = build_canonical_manifest_bytes(
        production_year=2026,
        source_document_sha256="a" * 64,
        rules_digest=digest,
        rule_count=len(sample_draft_rules),
        statement=statement,
    )
    sig = sign_payload_ed25519(priv, canon_bytes)

    att_rev = LegalAttestation(
        actor_id="OFFICER_A",
        role="LEGAL_REVIEWER",
        public_key_b64=pub,
        signature_b64=sig,
        signed_at="2026-02-01T10:00:00Z",
        statement=statement,
    )
    att_app = LegalAttestation(
        actor_id="OFFICER_B",
        role="LEGAL_APPROVER",
        public_key_b64=pub,
        signature_b64=sig,
        signed_at="2026-02-01T10:05:00Z",
        statement=statement,
    )

    with pytest.raises(SeparationOfDutiesViolation) as exc:
        pipeline.activate_rules(
            production_year=2026,
            reviewer_attestation=att_rev,
            approver_attestation=att_app,
            source_document_sha256="a" * 64,
        )
    assert "aynı genel anahtarı kullanamaz" in str(exc.value)


def test_invalid_signature_rejected(temp_archive: Path, sample_draft_rules: list[dict]):
    """Geçersiz imza sunulduğunda InvalidSignatureError fırlatıldığını test eder."""
    pipeline = RuleActivationPipeline(temp_archive)
    repo = DynamicRuleRepository(temp_archive)
    digest = repo.compute_rules_digest(2026)

    _, pub1 = generate_ed25519_keypair()
    priv2, pub2 = generate_ed25519_keypair()

    statement = "2026 kuralları incelendi ve onaylandı."
    canon_bytes = build_canonical_manifest_bytes(
        production_year=2026,
        source_document_sha256="a" * 64,
        rules_digest=digest,
        rule_count=len(sample_draft_rules),
        statement=statement,
    )

    sig2 = sign_payload_ed25519(priv2, canon_bytes)
    # Hatalı/sahte imza
    fake_sig = "A" * 88

    att_rev = LegalAttestation(
        actor_id="OFFICER_A",
        role="LEGAL_REVIEWER",
        public_key_b64=pub1,
        signature_b64=fake_sig,
        signed_at="2026-02-01T10:00:00Z",
        statement=statement,
    )
    att_app = LegalAttestation(
        actor_id="OFFICER_B",
        role="LEGAL_APPROVER",
        public_key_b64=pub2,
        signature_b64=sig2,
        signed_at="2026-02-01T10:05:00Z",
        statement=statement,
    )

    with pytest.raises(InvalidSignatureError):
        pipeline.activate_rules(
            production_year=2026,
            reviewer_attestation=att_rev,
            approver_attestation=att_app,
            source_document_sha256="a" * 64,
        )


def test_trusted_key_validation(temp_archive: Path, sample_draft_rules: list[dict]):
    """Güvenilir anahtar deposu tanımlandığında yabancı anahtarların reddedildiğini test eder."""
    pipeline = RuleActivationPipeline(temp_archive)
    repo = DynamicRuleRepository(temp_archive)
    digest = repo.compute_rules_digest(2026)

    priv1, pub1 = generate_ed25519_keypair()
    priv2, pub2 = generate_ed25519_keypair()
    _, trusted_other_pub = generate_ed25519_keypair()

    statement = "2026 kuralları incelendi ve onaylandı."
    canon_bytes = build_canonical_manifest_bytes(
        production_year=2026,
        source_document_sha256="a" * 64,
        rules_digest=digest,
        rule_count=len(sample_draft_rules),
        statement=statement,
    )
    sig1 = sign_payload_ed25519(priv1, canon_bytes)
    sig2 = sign_payload_ed25519(priv2, canon_bytes)

    att_rev = LegalAttestation(
        actor_id="OFFICER_A",
        role="LEGAL_REVIEWER",
        public_key_b64=pub1,
        signature_b64=sig1,
        signed_at="2026-02-01T10:00:00Z",
        statement=statement,
    )
    att_app = LegalAttestation(
        actor_id="OFFICER_B",
        role="LEGAL_APPROVER",
        public_key_b64=pub2,
        signature_b64=sig2,
        signed_at="2026-02-01T10:05:00Z",
        statement=statement,
    )

    # Güvenilir depoda reviewer anahtarı pub1 yerine trusted_other_pub kayıtlı
    trust_store = {
        "reviewer": {"public_key_b64": trusted_other_pub},
        "approver": {"public_key_b64": pub2},
    }

    with pytest.raises(TrustedKeyMismatchError):
        pipeline.activate_rules(
            production_year=2026,
            reviewer_attestation=att_rev,
            approver_attestation=att_app,
            source_document_sha256="a" * 64,
            trusted_keys=trust_store,
        )


# ---------------------------------------------------------------------------
# 4. Uçtan Uca Aktivasyon ve Evaluator Ödeme Kilidi Açma (DRAFT -> VERIFIED)
# ---------------------------------------------------------------------------

def test_full_activation_and_evaluator_lifecycle(temp_archive: Path, sample_draft_rules: list[dict]):
    """Taslak kuralların çift onay ile VERIFIED olması, payable_amount kilit açılması ve revoke süreci."""
    pipeline = RuleActivationPipeline(temp_archive)
    rule_repo = DynamicRuleRepository(temp_archive)

    # Aşama 1: DRAFT Durumu Değerlendirmesi
    catalog_draft = rule_repo.get_catalog([2026])
    eval_draft = DynamicSupportEvaluator.evaluate_parcel(
        catalog=catalog_draft,
        production_year=2026,
        as_of_date=date(2026, 6, 1),
        crop="BUĞDAY",
        area_da=Decimal("100.00"),
        province="KONYA",
        district="MERAM",
        cks_registered=True,
    )

    # Fail-closed doğrulaması: Taslak olduğu için payable_amount None olmalı!
    assert eval_draft.total_payable_amount is None
    assert eval_draft.total_proposed_amount == Decimal("48800.00")  # (244 + 244) * 100
    assert "Kurallar taslak (DRAFT)" in str(eval_draft.fail_closed_reason)

    # Aşama 2: Çift Onaylı Aktivasyon Yürütülmesi
    digest = rule_repo.compute_rules_digest(2026)
    priv1, pub1 = generate_ed25519_keypair()
    priv2, pub2 = generate_ed25519_keypair()

    statement = "2026 yılı kuralları yürürlüğe alınmıştır."
    canon_bytes = build_canonical_manifest_bytes(
        production_year=2026,
        source_document_sha256="a" * 64,
        rules_digest=digest,
        rule_count=len(sample_draft_rules),
        statement=statement,
    )

    sig1 = sign_payload_ed25519(priv1, canon_bytes)
    sig2 = sign_payload_ed25519(priv2, canon_bytes)

    att_rev = LegalAttestation(
        actor_id="REV_LEGAL_01",
        role="LEGAL_REVIEWER",
        public_key_b64=pub1,
        signature_b64=sig1,
        signed_at="2026-02-01T12:00:00Z",
        statement=statement,
    )
    att_app = LegalAttestation(
        actor_id="APP_BUDGET_02",
        role="LEGAL_APPROVER",
        public_key_b64=pub2,
        signature_b64=sig2,
        signed_at="2026-02-01T12:05:00Z",
        statement=statement,
    )

    manifest = pipeline.activate_rules(
        production_year=2026,
        reviewer_attestation=att_rev,
        approver_attestation=att_app,
        source_document_sha256="a" * 64,
    )

    assert manifest.status == "ACTIVE"
    assert manifest.rule_count == 2
    assert manifest.rules_digest == digest

    # Kural durumlarının VERIFIED olduğunu denetle
    counts = rule_repo.get_status_counts(2026)
    assert counts.get("VERIFIED") == 2
    assert counts.get("DRAFT", 0) == 0

    # WORM loguna 3 olayın eklendiğini doğrula
    worm = WormAuditLog(temp_archive)
    ok, _ = worm.verify_chain()
    assert ok is True
    blocks = worm.load_blocks()
    event_types = [b.event_type for b in blocks]
    assert "ATTESTATION_REVIEW" in event_types
    assert "ATTESTATION_APPROVAL" in event_types
    assert "RULE_ACTIVATION" in event_types

    # Aşama 3: VERIFIED Durumunda Değerlendirme (Ödeme Kilidi Açıldı!)
    catalog_verified = rule_repo.get_catalog([2026])
    eval_verified = DynamicSupportEvaluator.evaluate_parcel(
        catalog=catalog_verified,
        production_year=2026,
        as_of_date=date(2026, 6, 1),
        crop="BUĞDAY",
        area_da=Decimal("100.00"),
        province="KONYA",
        district="MERAM",
        cks_registered=True,
    )

    assert eval_verified.overall_status == "ELIGIBLE"
    assert eval_verified.total_payable_amount == Decimal("48800.00")
    assert eval_verified.fail_closed_reason is None

    # Aşama 4: Acil Durum İptali (REVOCATION)
    pipeline.revoke_activation(
        production_year=2026,
        actor_id="MINISTER_OFFICE",
        reason="Mükerrer Resmî Gazete ilanı nedeniyle acil yürütme durduruldu.",
    )

    status_info = pipeline.get_activation_status(2026)
    assert status_info["activation_status"] == "REVOKED"
    assert status_info["rules_counts"].get("REVOKED") == 2

    # Tekrar değerlendir: fail-closed devreye girdi, ödeme derhal kilitlendi!
    catalog_revoked = rule_repo.get_catalog([2026])
    eval_revoked = DynamicSupportEvaluator.evaluate_parcel(
        catalog=catalog_revoked,
        production_year=2026,
        as_of_date=date(2026, 6, 1),
        crop="BUĞDAY",
        area_da=Decimal("100.00"),
        province="KONYA",
        district="MERAM",
        cks_registered=True,
    )
    assert eval_revoked.total_payable_amount is None
    assert "Fail-Closed" in str(eval_revoked.fail_closed_reason)


# ---------------------------------------------------------------------------
# 5. FastAPI Admin Uç Noktaları Testi
# ---------------------------------------------------------------------------

def test_api_admin_rules_endpoints(monkeypatch, temp_archive: Path, sample_draft_rules: list[dict]):
    """P0-12 FastAPI uç noktalarını test eder."""
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(temp_archive))
    monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", "test_secret_key_123")

    client = TestClient(app)
    headers = {"X-Admin-Key": "test_secret_key_123"}

    # 1. Attestation Uç Noktası
    priv_rev, _ = generate_ed25519_keypair()
    priv_app, _ = generate_ed25519_keypair()

    resp_rev = client.post(
        "/admin/rules/attestation",
        headers=headers,
        json={
            "production_year": 2026,
            "actor_id": "API_REV_01",
            "role": "LEGAL_REVIEWER",
            "private_key_b64": priv_rev,
            "source_document_sha256": "a" * 64,
            "notes": "API test review",
        },
    )
    assert resp_rev.status_code == 200, resp_rev.text
    rev_data = resp_rev.json()
    assert rev_data["status"] == "ATTESTED_SUCCESSFULLY"

    resp_app = client.post(
        "/admin/rules/attestation",
        headers=headers,
        json={
            "production_year": 2026,
            "actor_id": "API_APP_02",
            "role": "LEGAL_APPROVER",
            "private_key_b64": priv_app,
            "source_document_sha256": "a" * 64,
            "notes": "API test approval",
        },
    )
    assert resp_app.status_code == 200, resp_app.text
    app_data = resp_app.json()

    # 2. Activation Uç Noktası
    resp_act = client.post(
        "/admin/rules/activate",
        headers=headers,
        json={
            "production_year": 2026,
            "source_document_sha256": "a" * 64,
            "reviewer_attestation": rev_data["attestation"],
            "approver_attestation": app_data["attestation"],
        },
    )
    assert resp_act.status_code == 200, resp_act.text
    act_data = resp_act.json()
    assert act_data["status"] == "ACTIVATED_SUCCESSFULLY"

    # 3. Status Uç Noktası
    resp_status = client.get("/admin/rules/activation-status?year=2026", headers=headers)
    assert resp_status.status_code == 200
    st_data = resp_status.json()
    assert st_data["activation_status"] == "ACTIVE"
    assert st_data["worm_chain_verified"] is True

    # 4. WORM Audit Uç Noktası
    resp_worm = client.get("/admin/rules/worm-audit?year=2026", headers=headers)
    assert resp_worm.status_code == 200
    w_data = resp_worm.json()
    assert w_data["verified"] is True
    assert len(w_data["history"]) >= 3

    # 5. Revoke Uç Noktası
    resp_revk = client.post(
        "/admin/rules/revoke",
        headers=headers,
        json={
            "production_year": 2026,
            "actor_id": "API_ADMIN",
            "reason": "Test iptal çağrısı",
        },
    )
    assert resp_revk.status_code == 200
    assert resp_revk.json()["status"] == "REVOKED_SUCCESSFULLY"

    # Durumun REVOKED olduğunu doğrula
    resp_status2 = client.get("/admin/rules/activation-status?year=2026", headers=headers)
    assert resp_status2.json()["activation_status"] == "REVOKED"
