"""Persist source-byte-bound PDF sentence geometry as DRAFT proof candidates.

A legal clause is not approved merely because bytes match; all objects created
here are technical evidence records, not legal authorization or payment data.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from tarim_destek_rag.auto_updater.pdf_grounding import PDFGroundingEngine
from tarim_destek_rag.database.models import (
    SentenceBoundingBoxModel,
    SourceDocumentModel,
    SourceModel,
)

SHA = re.compile(r"^[0-9a-f]{64}$")


def resolve_archived_pdf(root: Path, sha256: str) -> bytes:
    """Read only content-addressed PDF originals; no external URL or path traversal."""
    if not SHA.fullmatch(sha256):
        raise ValueError("PDF source hash is invalid")
    path = root / "originals" / (sha256 + ".pdf")
    if not path.is_file():
        raise FileNotFoundError("Original PDF evidence is unavailable")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError("Archived PDF source bytes were altered")
    return raw


def stage_evidence(
    session: Session, *,
    archive_root: Path,
    source_id: str,
    production_year: int,
    sha256: str,
    original_url: str,
    page_number: int,
    exact_quote: str,
    article: str | None = None,
    paragraph: str | None = None,
    clause: str | None = None,
) -> SentenceBoundingBoxModel:
    """Stage exact PDF text+coordinates, preserving source and quote identity."""
    if not 2020 <= production_year <= 2100:
        raise ValueError("Invalid production year")
    source = session.get(SourceModel, source_id)
    if source is None or not source.active or source.url != original_url:
        raise ValueError("Source is not an independently registered exact official URL")
    if source.content_type != "PDF":
        raise ValueError("Source is not registered as an official PDF")
    raw = resolve_archived_pdf(archive_root, sha256)
    grounded = PDFGroundingEngine.ground(
        raw,
        document_sha256=sha256,
        page_number=page_number,
        exact_quote=exact_quote,
        article=article,
        paragraph=paragraph,
        clause=clause,
    )
    document = session.scalar(
        select(SourceDocumentModel).where(
            SourceDocumentModel.document_sha256 == sha256,
            SourceDocumentModel.production_year == production_year,
            SourceDocumentModel.source_id == source_id,
        )
    )
    if document is None:
        document = SourceDocumentModel(
            source_id=source_id, production_year=production_year,
            document_sha256=sha256,
            original_url=original_url,
            archive_relative_path=f"originals/{sha256}.pdf",
            discovered_at=datetime.now(UTC),
            content_type="application/pdf",
            review_status="DRAFT",
        )
        session.add(document)
        session.flush()
    elif (
        document.source_id != source_id
        or document.production_year != production_year
        or document.original_url != original_url
        or document.review_status != "DRAFT"
    ):
        raise ValueError("Source document already exists with conflicting provenance")

    text_hash = hashlib.sha256(grounded.exact_quote.encode("utf-8")).hexdigest()
    existing = session.scalar(
        select(SentenceBoundingBoxModel).where(
            SentenceBoundingBoxModel.document_id == document.id,
            SentenceBoundingBoxModel.page_number == page_number,
            SentenceBoundingBoxModel.text_sha256 == text_hash,
        )
    )
    expected_boxes = json.dumps(grounded.to_dict()["bounding_boxes"], sort_keys=True)
    expected_quads = json.dumps(grounded.normalized_quads)
    if existing is not None:
        if (
            existing.exact_text != grounded.exact_quote
            or existing.bounding_boxes_json != expected_boxes
            or existing.normalized_quads_json != expected_quads
        ):
            raise ValueError("An existing PDF sentence bbox differs from original bytes")
        return existing

    row = SentenceBoundingBoxModel(
        document_id=document.id, page_number=page_number,
        exact_text=grounded.exact_quote, article_no=article,
        paragraph_no=paragraph, clause_no=clause,
        bounding_boxes_json=expected_boxes,
        normalized_quads_json=expected_quads,
        text_sha256=text_hash,
        review_status="DRAFT",
    )
    session.add(row)
    session.flush()
    return row


def load_grounded_sentence(
    session: Session, *,
    archive_root: Path,
    evidence_id: int,
    year: int,
):
    """Revalidate source identity + original PDF bytes on EVERY view request."""
    if evidence_id <= 0 or not 2020 <= year <= 2100:
        raise ValueError("Unsupported evidence identifier/production year")
    row = session.get(SentenceBoundingBoxModel, evidence_id)
    if row is None:
        raise LookupError("Unknown PDF legal sentence")
    doc = session.get(SourceDocumentModel, row.document_id)
    if doc is None or doc.production_year != year or doc.review_status != "DRAFT":
        raise LookupError("Document is unavailable or outside requested year")
    source = session.get(SourceModel, doc.source_id)
    if source is None or not source.active or source.url != doc.original_url:
        raise LookupError("Official source registration is missing or has changed")
    raw = resolve_archived_pdf(archive_root, doc.document_sha256)
    grounded = PDFGroundingEngine.ground(
        raw, document_sha256=doc.document_sha256,
        page_number=row.page_number, exact_quote=row.exact_text,
        article=row.article_no, paragraph=row.paragraph_no, clause=row.clause_no,
    )
    if (
        json.loads(row.bounding_boxes_json) != grounded.to_dict()["bounding_boxes"]
        or json.loads(row.normalized_quads_json) != grounded.normalized_quads
        or row.text_sha256 != hashlib.sha256(row.exact_text.encode("utf-8")).hexdigest()
    ):
        raise ValueError("PDF sentence geometry does not match archived source")
    return row, doc, grounded, raw
