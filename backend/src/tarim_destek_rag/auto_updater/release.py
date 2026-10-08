"""Year-neutral, independently signed legal release manifest; fail closed.

A release groups EXACT approved rate components, source PDF sentences and
deterministic predicates. Two legal officers sign the canonical manifest as a
RELEASE subject. Every referenced rate must also have its OWN two signatures.
No draft-to-payment, demo seed, incomplete coverage or non-WORM fallback.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.auto_updater.grounding_repository import load_grounded_sentence
from tarim_destek_rag.database.legal_approvals import subject_digest, two_person_approved
from tarim_destek_rag.database.models import (
    DynamicRateModel, LegalReleaseModel, SourceVersionModel, VerifiedSupportRateModel,
)
from tarim_destek_rag.rules.dynamic_engine import DynamicRuleEngine

_REQUIRED_COVERAGE = {
    "official_sources", "program_terms", "monetary_rates",
    "geography", "exceptions", "application_period", "gold_cases",
}
_MANIFEST_KEYS = {
    "schema_version", "production_year", "source_versions",
    "entries", "coverage", "coverage_review_reference",
}


@dataclass(frozen=True)
class ReleaseAssessment:
    status: str
    reason: str
    release_id: int | None = None
    manifest_sha256: str | None = None


def canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _hash(value: dict) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _manifest(manifest: dict, year: int) -> dict:
    if (
        not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS
        or manifest["schema_version"] != 1
        or type(manifest["production_year"]) is not int
        or manifest["production_year"] != year
    ):
        raise ValueError("Release schema/year does not match production year")
    coverage = manifest["coverage"]
    if not isinstance(coverage, dict) or set(coverage) != _REQUIRED_COVERAGE:
        raise ValueError("All legal coverage categories must be acknowledged")
    if any(type(x) is not bool for x in coverage.values()):
        raise ValueError("Coverage is not a boolean legal checklist")
    if not isinstance(manifest["coverage_review_reference"], str):
        raise ValueError("Legal coverage review evidence is required")
    if not 8 <= len(manifest["coverage_review_reference"]) <= 256:
        raise ValueError("Legal coverage review reference invalid")
    entries = manifest["entries"]
    refs = manifest["source_versions"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 1000:
        raise ValueError("At least one bounded legal release rate is required")
    if not isinstance(refs, list) or not 1 <= len(refs) <= 1000:
        raise ValueError("Release needs original source document version references")
    if any(
        not isinstance(r, dict) or set(r) != {"id", "sha256"}
        or type(r["id"]) is not int or r["id"] <= 0
        or not isinstance(r["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", r["sha256"])
        for r in refs
    ) or len(set(r["id"] for r in refs)) != len(refs):
        raise ValueError("Invalid/duplicate source version references")
    keys = []
    for e in entries:
        if not isinstance(e, dict) or set(e) != {
            "program_key", "crop_code", "rate_id", "rate_subject_digest",
            "candidate_id", "candidate_sha256", "evidence_id", "conditions",
            "province", "district",
        }:
            raise ValueError("Malformed legal release rule")
        if any(type(e[k]) is not int or e[k] <= 0
               for k in ("rate_id", "candidate_id", "evidence_id")):
            raise ValueError("Each release needs a real rate/candidate/evidence record")
        if not isinstance(e["rate_subject_digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", e["rate_subject_digest"]):
            raise ValueError("Signed rate digest missing")
        if not isinstance(e["candidate_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", e["candidate_sha256"]):
            raise ValueError("Signed candidate digest missing")
        for k in ("program_key", "crop_code", "province", "district"):
            if not isinstance(e[k], str) or not e[k].strip():
                raise ValueError("Malformed legal release classification")
        if (e["province"] == "*") != (e["district"] == "*"):
            raise ValueError("National/local scope must be explicit")
        DynamicRuleEngine.check(e["conditions"], {})
        keys.append((e["program_key"], e["crop_code"], e["province"], e["district"]))
    if len(keys) != len(set(keys)):
        raise ValueError("Ambiguous duplicate rate applicability")
    # Ambiguous overlap across local and national rows is NOT resolved by order.
    group = {}
    for program, crop, province, district in keys:
        group.setdefault((program, crop), set()).add((province, district))
    if any(("*", "*") in scopes and len(scopes) > 1 for scopes in group.values()):
        raise ValueError("Overlapping national/local entries must be disambiguated")
    return manifest


def candidate_digest(candidate: DynamicRateModel) -> str:
    """Bind every Decimal, source link, date and status of the DRAFT candidate."""
    payload = {
        "id": candidate.id,
        "program_key": candidate.program_key,
        "crop_code": candidate.crop_code,
        "production_year": candidate.production_year,
        "province": candidate.province,
        "district": candidate.district,
        "base_coefficient": format(candidate.base_coefficient, "f"),
        "category_multiplier": format(candidate.category_multiplier, "f"),
        "proposed_unit_amount": format(candidate.proposed_unit_amount, "f"),
        "unit": candidate.unit,
        "effective_from": candidate.effective_from.isoformat(),
        "effective_to": candidate.effective_to.isoformat() if candidate.effective_to else None,
        "source_sentence_id": candidate.source_sentence_id,
        "review_status": candidate.review_status,
    }
    return _hash(payload)


def stage_release(
    session: Session, *, manifest: dict, source_version_id: int,
    effective_from: date, effective_to: date | None = None,
) -> LegalReleaseModel:
    """Creates DRAFT only. Does not sign, verify or activate anything."""
    year = manifest.get("production_year")
    _manifest(manifest, year)
    if not isinstance(effective_from, date) or (
        effective_to is not None and effective_to < effective_from
    ):
        raise ValueError("Invalid release effective period")
    source = session.get(SourceVersionModel, source_version_id)
    refs = {r["id"]: r["sha256"] for r in manifest["source_versions"]}
    if source is None or refs.get(source_version_id) != source.content_hash:
        raise ValueError("Release anchor source hash not in declared source evidence")
    content = canonical_json(manifest)
    digest = hashlib.sha256(content.encode()).hexdigest()
    existing = session.scalar(select(LegalReleaseModel).where(
        LegalReleaseModel.production_year == year,
        LegalReleaseModel.manifest_sha256 == digest,
    ))
    if existing:
        if (
            existing.manifest_json != content
            or existing.source_version_id != source_version_id
            or existing.effective_from != effective_from
            or existing.effective_to != effective_to
        ):
            raise ValueError("Conflicting snapshot for existing hash")
        return existing
    snap = LegalReleaseModel(
        production_year=year, source_version_id=source_version_id,
        manifest_json=content, manifest_sha256=digest,
        effective_from=effective_from, effective_to=effective_to,
        coverage_complete=False, review_status="DRAFT",
    )
    session.add(snap)
    session.flush()
    return snap


def _check_release(
    session: Session, *, snapshot: LegalReleaseModel,
    archive_root: Path, when: date,
) -> dict | None:
    if (
        snapshot.review_status != "VERIFIED"
        or not snapshot.coverage_complete
        or not snapshot.reviewed_by or not snapshot.reviewed_at
        or not snapshot.review_reference
        or snapshot.effective_from > when
        or (snapshot.effective_to is not None and snapshot.effective_to < when)
    ):
        return None
    try:
        manifest = _manifest(json.loads(snapshot.manifest_json), snapshot.production_year)
        if _hash(manifest) != snapshot.manifest_sha256:
            return None
        if not all(manifest["coverage"].values()):
            return None
        if not two_person_approved(session, snapshot):
            return None
        source_refs = {
            item["id"]: item["sha256"] for item in manifest["source_versions"]
        }
        if source_refs.get(snapshot.source_version_id) != snapshot.source_version.content_hash:
            return None
        for ident, digest in source_refs.items():
            version = session.get(SourceVersionModel, ident)
            if (
                version is None or version.content_hash != digest
                or version.superseded or version.source is None
                or not version.source.active
            ):
                return None
        for entry in manifest["entries"]:
            rate = session.get(VerifiedSupportRateModel, entry["rate_id"])
            candidate = session.get(DynamicRateModel, entry["candidate_id"])
            if rate is None or candidate is None:
                return None
            if (
                rate.production_year != snapshot.production_year
                or candidate.production_year != snapshot.production_year
                or candidate.review_status != "DRAFT"
                or rate.crop_name != entry["crop_code"]
                or candidate.crop_code != entry["crop_code"]
                or candidate.program_key != entry["program_key"]
                or not (
                    rate.program_id == entry["program_key"]
                    or rate.program_id == f"{entry['program_key']}_{snapshot.production_year}"
                )
                or rate.province != entry["province"]
                or rate.district != entry["district"]
                or candidate.province != entry["province"]
                or candidate.district != entry["district"]
                or candidate.source_sentence_id != entry["evidence_id"]
                or candidate_digest(candidate) != entry["candidate_sha256"]
                or rate.unit_amount != candidate.proposed_unit_amount
                or rate.unit != "TRY/da" or candidate.unit != "TRY/da"
                or not rate.legal_clause or not rate.legal_clause.strip()
                or not rate.approved_by or not rate.approved_at
                or not rate.review_reference
                or not rate.source_version.effective_from
                or rate.source_version.effective_from > when.isoformat()
                or (rate.source_version.effective_to
                    and rate.source_version.effective_to < when.isoformat())
                or candidate.effective_from != rate.effective_from
                or candidate.effective_to != rate.effective_to
                or rate.effective_from > when
                or (rate.effective_to and rate.effective_to < when)
                or source_refs.get(rate.source_version_id) != rate.source_version.content_hash
                or subject_digest(rate) != entry["rate_subject_digest"]
                or not two_person_approved(session, rate)
            ):
                return None
            sentence, doc, grounded, _ = load_grounded_sentence(
                session, archive_root=archive_root,
                evidence_id=entry["evidence_id"], year=snapshot.production_year,
            )
            if (
                doc.document_sha256 != rate.source_version.content_hash
                or doc.source_id != rate.source_version.source_id
                or doc.original_url != rate.source_version.source.url
                or not sentence.exact_text
            ):
                return None
        # A separately VERIFIED rate omitted from the release for this
        # program/crop/year could shadow the manifest under a more specific
        # province/district. Refuse such ambiguities rather than picking an
        # arbitrary rate in a future-year rollout.
        declared = {e["rate_id"] for e in manifest["entries"]}
        for entry in manifest["entries"]:
            matches = list(session.scalars(select(VerifiedSupportRateModel).where(
                VerifiedSupportRateModel.program_id.in_(
                    (entry["program_key"],
                     f"{entry['program_key']}_{snapshot.production_year}")
                ),
                VerifiedSupportRateModel.crop_name == entry["crop_code"],
                VerifiedSupportRateModel.production_year == snapshot.production_year,
                VerifiedSupportRateModel.review_status == "VERIFIED",
                VerifiedSupportRateModel.effective_from <= when,
            )).all())
            for other in matches:
                if (
                    (other.effective_to is None or other.effective_to >= when)
                    and other.id not in declared
                ):
                    return None
        return manifest
    except (ValueError, LookupError, KeyError, TypeError, AttributeError,
            json.JSONDecodeError, OSError, FileNotFoundError):
        return None


def resolve_active_release(
    session: Session, *, year: int, when: date, archive_root: Path,
) -> tuple[ReleaseAssessment, dict | None]:
    """No implicit default year, no selection by latest row or merge order."""
    if type(year) is not int or not 2020 <= year <= 2100:
        return ReleaseAssessment("HOLD", "Invalid production year"), None
    candidates = list(session.scalars(select(LegalReleaseModel).where(
        LegalReleaseModel.production_year == year,
        LegalReleaseModel.review_status == "VERIFIED",
        LegalReleaseModel.effective_from <= when,
    )).all())
    valid = []
    for release in candidates:
        manifest = _check_release(
            session, snapshot=release, archive_root=archive_root, when=when
        )
        if manifest is not None:
            valid.append((release, manifest))
    if len(valid) != 1:
        return ReleaseAssessment(
            "HOLD", "No uniquely signed, fully sourced release for requested year"
        ), None
    release, manifest = valid[0]
    return ReleaseAssessment(
        "ACTIVE", "Independently signed and revalidated release",
        release_id=release.id, manifest_sha256=release.manifest_sha256,
    ), manifest


def evaluate_release(
    session: Session, *, archive_root: Path, year: int, when: date,
    program_key: str, crop_code: str, province: str, district: str,
    area_da: Decimal, facts: dict,
) -> dict:
    """No bypass of independently signed rates or complete release coverage."""
    assessment, manifest = resolve_active_release(
        session, year=year, when=when, archive_root=archive_root,
    )
    hold = {"status": "REVIEW", "estimated_amount": None,
            "release_id": assessment.release_id, "reason": assessment.reason}
    if manifest is None:
        return hold
    if not isinstance(area_da, Decimal) or not area_da.is_finite() or area_da <= 0:
        return {**hold, "reason": "Verified positive Decimal parcel area required"}
    applicable = [
        e for e in manifest["entries"]
        if e["program_key"] == program_key and e["crop_code"] == crop_code
        and (e["province"], e["district"]) in (("*", "*"), (province, district))
    ]
    if len(applicable) != 1:
        return {**hold, "reason": "Rule missing or overlapping for geographic scope"}
    entry = applicable[0]
    checks = DynamicRuleEngine.check(entry["conditions"], facts)
    if not checks or not all(x.startswith("MATCHED:") for x in checks):
        return {**hold, "reason": "Unproven farmer eligibility or exception", "checks": checks}
    rate = session.get(VerifiedSupportRateModel, entry["rate_id"])
    amount = (rate.unit_amount * area_da).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    # A legally current RATE is NOT a verified farmer-specific entitlement.
    # Actual ÇKS/parsel ownership/evidence is a separate trusted input gate.
    # This endpoint never grants a payout on self-asserted facts; a separate
    # verified farmer evidence service must be integrated in P0-8D.
    return {
        "status": "REVIEW",
        "estimated_amount": None,
        "simulated_amount": str(amount),
        "unit_amount": str(rate.unit_amount),
        "release_id": assessment.release_id,
        "source_evidence_id": entry["evidence_id"],
        "release_manifest_sha256": assessment.manifest_sha256,
        "reason": "Legal rate release signed; farmer-specific evidence NOT verified",
    }
