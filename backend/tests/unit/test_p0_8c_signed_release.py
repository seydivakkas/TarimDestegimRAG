"""P0-8C signed 2030 release: local synthetic keys and synthetic clauses ONLY.

No real legal official, KMS/HSM, WORM or production activation exists in CI.
"""

import base64
import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal

import pymupdf
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.auto_updater.grounding_repository import stage_evidence
from tarim_destek_rag.auto_updater.release import (
    candidate_digest,
    evaluate_release,
    resolve_active_release,
    stage_release,
)
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.legal_approvals import (
    register_detached_approval,
    register_detached_revocation,
    revocation_message,
    subject_digest,
    two_person_approved,
)
from tarim_destek_rag.database.models import (
    DynamicRateModel,
    SourceModel,
    SourceVersionModel,
    SupportProgramModel,
    VerifiedSupportRateModel,
)

from backend.tests.legal_approval_testkit import detached_envelope, trust_pair

SOURCE_URL = "https://www.resmigazete.gov.tr/eskiler/2030/02/20300202-1.pdf"
CLAUSE = "Synthetic 2030 law proof: a registered parcel has the stated rate."


@pytest.fixture
def repo_fixture(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((25, 110), CLAUSE, fontsize=10)
        raw = document.tobytes()
        document.close()
        sha = hashlib.sha256(raw).hexdigest()
        original_dir = tmp_path / "originals"
        original_dir.mkdir()
        (original_dir / f"{sha}.pdf").write_bytes(raw)
        session.add(SourceModel(
            source_id="RG-SYNTHETIC-2030", url=SOURCE_URL,
            title="Synthetic legal source", authority="OFFICIAL_GAZETTE",
            active=True, content_type="PDF",
        ))
        session.add(SupportProgramModel(
            id="BASIC_SUPPORT_2030", name="Synthetic base support",
            year=2030, active=True,
        ))
        session.flush()
        version = SourceVersionModel(
            source_id="RG-SYNTHETIC-2030", content_hash=sha,
            detected_at="2030-01-02T08:00:00Z", version=1, superseded=False,
            effective_from="2030-01-01",
        )
        session.add(version)
        session.flush()
        sentence = stage_evidence(
            session, archive_root=tmp_path, source_id="RG-SYNTHETIC-2030",
            production_year=2030, sha256=sha, original_url=SOURCE_URL,
            page_number=1, exact_quote=CLAUSE, article="Madde 6",
        )
        rate = VerifiedSupportRateModel(
            program_id="BASIC_SUPPORT_2030", crop_name="BUGDAY",
            production_year=2030, province="*", district="*",
            unit_amount=Decimal("125.00"), unit="TRY/da",
            effective_from=date(2030, 1, 1), effective_to=None,
            source_version_id=version.id, legal_clause="Madde 6 / 2",
            review_status="VERIFIED", approved_by="synthetic-legal-owner",
            approved_at=datetime.now(UTC),
            review_reference="SYNTHETIC-UNIT-TEST",
        )
        session.add(rate)
        candidate = DynamicRateModel(
            program_key="BASIC_SUPPORT", crop_code="BUGDAY",
            production_year=2030, province="*", district="*",
            base_coefficient=Decimal("100.00"),
            category_multiplier=Decimal("1.2500"),
            proposed_unit_amount=Decimal("125.00"), unit="TRY/da",
            effective_from=date(2030, 1, 1),
            source_sentence_id=sentence.id, review_status="DRAFT",
        )
        session.add(candidate)
        session.flush()
        yield session, tmp_path, version, rate, candidate, sentence
        session.rollback()
    engine.dispose()


def manifest_for(version, rate, candidate, sentence, *, complete=True):
    return {
        "schema_version": 1, "production_year": 2030,
        "source_versions": [{"id": version.id, "sha256": version.content_hash}],
        "coverage": {
            item: complete for item in (
                "official_sources", "program_terms", "monetary_rates",
                "geography", "exceptions", "application_period", "gold_cases"
            )
        },
        "coverage_review_reference": "SYNTHETIC-REVIEW-ONLY",
        "entries": [{
            "program_key": "BASIC_SUPPORT", "crop_code": "BUGDAY",
            "rate_id": rate.id, "rate_subject_digest": subject_digest(rate),
            "candidate_id": candidate.id,
            "candidate_sha256": candidate_digest(candidate),
            "evidence_id": sentence.id,
            "province": "*", "district": "*",
            "conditions": {"all_of": [
                {"field": "cks_registered", "op": "eq", "value": True},
                {"field": "crop_code", "op": "eq", "value": "BUGDAY"},
            ]},
        }],
    }


def sign_two(session, subject, signers):
    for role in ("REVIEWER", "APPROVER"):
        register_detached_approval(session, subject, detached_envelope(subject, role, signers))
    session.flush()


def reviewed_release(session, version, manifest):
    release = stage_release(
        session, manifest=manifest, source_version_id=version.id,
        effective_from=date(2030, 1, 1),
    )
    # Not an API; this manual fixture simulates a separately controlled DBA
    # reviewing the material before the two independent detached signatures.
    release.review_status = "VERIFIED"
    release.coverage_complete = True
    release.reviewed_by = "synthetic-legal-organization"
    release.reviewed_at = datetime.now(UTC)
    release.review_reference = "SYNTHETIC-LEGAL-COVERAGE-NOT-REAL"
    session.flush()
    return release


def test_unsigned_future_release_is_hold_even_with_verified_rate(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    release = reviewed_release(session, version, manifest_for(version, rate, candidate, sentence))
    assert two_person_approved(session, release) is False
    assessment, content = resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )
    assert assessment.status == "HOLD" and content is None


def test_double_synthetic_signatures_select_release_but_not_farmer_payment(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    release = reviewed_release(session, version, manifest_for(version, rate, candidate, sentence))
    sign_two(session, release, signers)
    assert two_person_approved(session, release)
    assessment, manifest = resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )
    assert assessment.status == "ACTIVE"
    assert assessment.release_id == release.id
    assert manifest["production_year"] == 2030
    result = evaluate_release(
        session, archive_root=archive, year=2030, when=date(2030, 4, 1),
        program_key="BASIC_SUPPORT", crop_code="BUGDAY",
        province="KONYA", district="KARATAY", area_da=Decimal("2.0"),
        facts={"cks_registered": True, "crop_code": "BUGDAY"},
    )
    assert result["status"] == "REVIEW"
    assert result["estimated_amount"] is None
    assert result["simulated_amount"] == "250.00"
    assert result["source_evidence_id"] == sentence.id
    wrong_year = evaluate_release(
        session, archive_root=archive, year=2029, when=date(2029, 4, 1),
        program_key="BASIC_SUPPORT", crop_code="BUGDAY",
        province="KONYA", district="KARATAY", area_da=Decimal("2.0"),
        facts={"cks_registered": True, "crop_code": "BUGDAY"},
    )
    assert wrong_year["status"] == "REVIEW"
    assert wrong_year["estimated_amount"] is None


def test_changed_rate_or_proof_invalidates_all_release_signatures(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    release = reviewed_release(session, version, manifest_for(version, rate, candidate, sentence))
    sign_two(session, release, signers)
    candidate.category_multiplier = Decimal("2.5000")
    session.flush()
    assessment, content = resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )
    assert assessment.status == "HOLD" and content is None


def test_modified_original_pdf_and_source_revocation_close_release(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    release = reviewed_release(session, version, manifest_for(version, rate, candidate, sentence))
    sign_two(session, release, signers)
    (archive / "originals" / (version.content_hash + ".pdf")).write_bytes(b"forged")
    assessment, content = resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )
    assert assessment.status == "HOLD" and content is None


def test_draft_release_never_auto_signs_or_goes_live(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    release = stage_release(
        session, manifest=manifest_for(version, rate, candidate, sentence),
        source_version_id=version.id, effective_from=date(2030, 1, 1),
    )
    assert release.review_status == "DRAFT"
    assessment, content = resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )
    assert assessment.status == "HOLD" and content is None


def test_unreviewed_coverage_or_missing_legal_rate_denied(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    manifest = manifest_for(version, rate, candidate, sentence, complete=False)
    release = reviewed_release(session, version, manifest)
    sign_two(session, release, signers)
    assessment, content = resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )
    assert assessment.status == "HOLD"
    assert content is None


def test_missing_real_global_activation_switch_keeps_release_on_hold(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    release = reviewed_release(session, version, manifest_for(version, rate, candidate, sentence))
    sign_two(session, release, signers)
    monkeypatch.delenv("TARIM_RAG_LEGAL_ACTIVATION_ENABLED")
    assert resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )[0].status == "HOLD"


def test_mutating_signed_release_manifest_invalidates_digest(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    release = reviewed_release(session, version, manifest_for(version, rate, candidate, sentence))
    sign_two(session, release, signers)
    release.manifest_json = release.manifest_json.replace("SYNTHETIC-REVIEW-ONLY", "CHANGED-REVIEW-ONLY")
    session.flush()
    assert resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )[0].status == "HOLD"


def test_competing_signed_releases_for_same_year_fail_closed(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    first_manifest = manifest_for(version, rate, candidate, sentence)
    first = reviewed_release(session, version, first_manifest)
    sign_two(session, first, signers)
    second_manifest = manifest_for(version, rate, candidate, sentence)
    second_manifest["coverage_review_reference"] = "SYNTHETIC-SECOND-REVIEW"
    second = reviewed_release(session, version, second_manifest)
    sign_two(session, second, signers)
    assert first.id != second.id
    status, content = resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )
    assert status.status == "HOLD" and content is None


def test_signed_approver_revocation_disables_active_release(repo_fixture, monkeypatch):
    session, archive, version, rate, candidate, sentence = repo_fixture
    signers = trust_pair(monkeypatch)
    sign_two(session, rate, signers)
    release = reviewed_release(
        session, version, manifest_for(version, rate, candidate, sentence)
    )
    sign_two(session, release, signers)
    assert resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )[0].status == "ACTIVE"
    principal, private = signers["APPROVER"]
    now = datetime.now(UTC).isoformat(timespec="seconds")
    digest = subject_digest(release)
    reason = "Synthetic amended law replaced previous 2030 source"
    signature = private.sign(revocation_message(
        kind="RELEASE", record_id=release.id, digest=digest,
        source_sha256=release.source_version.content_hash,
        principal_id=principal, signed_at=now, reason=reason,
    ))
    register_detached_revocation(session, release, {
        "principal_id": principal, "reason": reason,
        "signed_at": now, "subject_digest": digest,
        "source_sha256": release.source_version.content_hash,
        "signature_b64": base64.b64encode(signature).decode(),
    })
    assert resolve_active_release(
        session, year=2030, when=date(2030, 4, 1), archive_root=archive,
    )[0].status == "HOLD"


def test_overlapping_release_geographic_rates_rejected(repo_fixture):
    session, archive, version, rate, candidate, sentence = repo_fixture
    bad = manifest_for(version, rate, candidate, sentence)
    bad["entries"].append(dict(bad["entries"][0], province="KONYA", district="KARATAY"))
    with pytest.raises(ValueError, match="Overlapping"):
        stage_release(
            session, manifest=bad, source_version_id=version.id,
            effective_from=date(2030, 1, 1),
        )
