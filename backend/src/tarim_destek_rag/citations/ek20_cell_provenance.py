"""EK-20: original-pixel ROI proposal and two-person signed visual review.

A valid dual review proves two registered keys signed one exact image ROI and
visual transcription. It NEVER establishes legislation effective-year validity,
farmer eligibility, support entitlement or permission to activate payments.

No reviewer keys, ROI proposals, or approvals ship with the application.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

from tarim_destek_rag.citations.pdf_page_indexer import get_global_pdf_indexer

DPI = 180
SCHEMA = 1
DOC_ID = "RG_AMENDMENT_2025_42_ANNEX"
FIELD_IDS = (
    "biological_tl_da", "biotechnical_tl_da",
    "feromone_trap_tl_da", "feromone_only_tl_da",
)
_SLUG = re.compile(r"[a-z][a-z0-9_]{1,60}")
_HEX = re.compile(r"[a-f0-9]{64}")
_MAX_FILE = 100_000


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > _MAX_FILE:
        raise ValueError("Missing or oversized signed-review file")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Review document must be an object")
    return data


def _root(env: str, fallback: str) -> Path:
    return Path(os.getenv(env, fallback))


def _proposal_path(sha: str, row: str, field: str) -> Path:
    if not _HEX.fullmatch(sha) or not _SLUG.fullmatch(row) or field not in FIELD_IDS:
        raise ValueError("Invalid proposal selector")
    return _root(
        "TARIM_RAG_EK20_PROPOSAL_DIR", "data/ek20_review_proposals",
    ) / sha / (row + "__" + field + ".json")


def _review_dir(sha: str, row: str, field: str) -> Path:
    return _root(
        "TARIM_RAG_EK20_REVIEW_DIR", "data/ek20_signed_reviews",
    ) / sha / (row + "__" + field)


def _original_context(row: str, field: str) -> dict[str, Any]:
    """Revalidate originals, transcription and current exact RGB pixels."""
    from PIL import Image
    from tarim_destek_rag.citations.ek20_review_workbench import _table

    if not isinstance(row, str) or not _SLUG.fullmatch(row) or field not in FIELD_IDS:
        raise ValueError("Invalid EK-20 row/field identifier")
    table = _table()
    if table is None:
        raise ValueError("Unverified EK-20 visual transcription")
    matches = [r for r in table["rows"] if r.get("row_id") == row]
    if len(matches) != 1 or field not in matches[0]:
        raise ValueError("Missing or duplicate EK-20 transcription field")
    value = matches[0][field]
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError("Unsupported unit amount")
    idx = get_global_pdf_indexer()
    record = idx.get_page(DOC_ID, 1)
    if record is None or record.total_pages != 1:
        raise ValueError("Original EK-20 PDF has no verified single page")
    original, _ = idx._verified_pdf(DOC_ID)
    if (original["original_sha256"] != table["source_sha256"]
            or original["url"] != table["source_url"]
            or record.source_sha256 != original["original_sha256"]
            or record.official_url != original["url"] + "#page=1"):
        raise ValueError("EK-20 original/source identity mismatch")
    png, highlights, sha = idx.screenshot(record, dpi=DPI)
    if highlights or sha != original["original_sha256"]:
        raise ValueError("Original pixel identity mismatch")
    with Image.open(io.BytesIO(png)) as src:
        rgb = src.convert("RGB")
    return {
        "record": record, "table": table, "row": matches[0], "value": value,
        "image": rgb, "sha": sha, "url": original["url"],
    }


def _pixel_sha(image: Any) -> str:
    """Digest of RGB pixel bytes and dimensions (not encoder PNG metadata)."""
    w, h = image.size
    return hashlib.sha256(
        b"ek20-rgb-v1\0" + w.to_bytes(4, "big")
        + h.to_bytes(4, "big") + image.convert("RGB").tobytes()
    ).hexdigest()


def prepare_roi(row: str, field: str, bbox: list[int]) -> dict[str, Any]:
    """Build source-derived proposal for a human-selected PIXEL rectangle."""
    ctx = _original_context(row, field)
    image = ctx["image"]
    if (type(bbox) is not list or len(bbox) != 4
            or any(type(n) is not int for n in bbox)):
        raise ValueError("ROI must contain four integer image coordinates")
    x0, y0, x1, y1 = bbox
    if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height
            and x1-x0 >= 8 and y1-y0 >= 8
            and (x1-x0)*(y1-y0) <= image.width*image.height//4):
        raise ValueError("ROI is outside the real image or unreasonably large")
    proposal = {
        "schema_version": SCHEMA,
        "source_id": DOC_ID,
        "source_sha256": ctx["sha"],
        "source_url": ctx["url"],
        "source_page": 1,
        "production_year": 2026,
        "render_dpi": DPI,
        "image_size": [image.width, image.height],
        "page_rgb_sha256": _pixel_sha(image),
        "row_id": row,
        "row_label": ctx["row"]["product_pest"],
        "field": field,
        "visual_transcription": ctx["value"],  # null is NOT zero
        "unit": "TRY_PER_DECARE",
        "pixel_bbox": bbox,
        "roi_rgb_sha256": _pixel_sha(image.crop(tuple(bbox))),
        "status": "ROI_PROPOSED_UNREVIEWED",
    }
    return proposal


def _trusted_reviewers() -> dict[str, tuple[str, Ed25519PublicKey, bytes]]:
    """Only local admin-pinned, active and unique reviewer keys are trusted."""
    path = os.getenv("TARIM_RAG_EK20_REVIEWER_REGISTRY")
    if not path:
        raise ValueError("Local reviewer trust registry is not configured")
    data = _read_json(Path(path))
    if data.get("schema_version") != 1 or not isinstance(data.get("reviewers"), list):
        raise ValueError("Invalid reviewer registry")
    reviewers: dict[str, tuple[str, Ed25519PublicKey, bytes]] = {}
    known_keys: set[bytes] = set()
    for item in data["reviewers"]:
        if (not isinstance(item, dict) or item.get("active") is not True):
            continue
        name, role = item.get("reviewer_id"), item.get("role")
        if (not isinstance(name, str) or not _SLUG.fullmatch(name)
                or role not in ("primary", "independent")
                or name in reviewers):
            raise ValueError("Reviewer identity or role is invalid/ambiguous")
        pem = item.get("public_key_pem")
        if not isinstance(pem, str) or len(pem) > 5000:
            raise ValueError("Invalid reviewer public key")
        key = serialization.load_pem_public_key(pem.encode("ascii"))
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("Review keys must be Ed25519")
        raw = key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        if raw in known_keys:
            raise ValueError("Multiple reviewer identities share one key")
        known_keys.add(raw)
        reviewers[name] = (role, key, raw)
    return reviewers


def _review_payload(
    proposal: dict[str, Any], reviewer: str, role: str, decision: str,
    reviewed_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA, "proposal": proposal,
        "reviewer_id": reviewer, "role": role, "decision": decision,
        "reviewed_at": reviewed_at,
        "scope": "VISUAL_CELL_LOCATION_AND_TRANSCRIPTION_ONLY",
    }


def _valid_record(
    obj: dict[str, Any],
    trusted: dict[str, tuple[str, Ed25519PublicKey, bytes]],
) -> tuple[str, str, str, bytes, dict[str, Any]]:
    signed, signature = obj.get("signed"), obj.get("signature_b64")
    if not isinstance(signed, dict) or not isinstance(signature, str):
        raise ValueError("Unsigned visual review")
    reviewer = signed.get("reviewer_id")
    if reviewer not in trusted:
        raise ValueError("Unknown/revoked reviewer")
    role, key, raw = trusted[reviewer]
    if signed.get("role") != role or signed.get("decision") not in ("APPROVE", "REJECT"):
        raise ValueError("Review role or decision invalid")
    proposal = signed.get("proposal")
    when = signed.get("reviewed_at")
    if (not isinstance(proposal, dict) or not isinstance(when, str)
            or len(when) > 40 or not when.endswith("+00:00")
            or _review_payload(
                proposal, reviewer, role, signed["decision"], when,
            ) != signed):
        raise ValueError("Noncanonical review identity or content")
    try:
        key.verify(base64.b64decode(signature, validate=True), canonical(signed))
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("Invalid review signature") from exc
    return reviewer, role, signed["decision"], raw, proposal


def verdict(row: str, field: str) -> dict[str, Any]:
    """Fail closed until two distinct active identities sign ONE exact ROI."""
    try:
        ctx = _original_context(row, field)
        path = _proposal_path(ctx["sha"], row, field)
        if not path.is_file():
            return {"status": "NO_AUTHENTIC_ROI_PROPOSAL", "proposal": None}
        draft = _read_json(path)
        expected = prepare_roi(row, field, draft.get("pixel_bbox"))
        if draft != expected:
            raise ValueError("The proposal does not match current source pixels")
        reviews_dir = _review_dir(ctx["sha"], row, field)
        if not reviews_dir.is_dir():
            return {"status": "ROI_PROPOSED_UNREVIEWED", "proposal": expected}
        review_paths = sorted(reviews_dir.glob("*.json"))
        if not review_paths:
            return {"status": "ROI_PROPOSED_UNREVIEWED", "proposal": expected}
        if len(review_paths) > 20:
            raise ValueError("Unexpected review record count")
        trusted = _trusted_reviewers()
        approved_roles: set[str] = set()
        approved_keys: set[bytes] = set()
        reviewer_ids: set[str] = set()
        for file in review_paths:
            person, role, decision, raw, signed_proposal = _valid_record(
                _read_json(file), trusted,
            )
            if (file.stem != person or person in reviewer_ids
                    or signed_proposal != expected):
                raise ValueError("Conflicting or misattributed review record")
            reviewer_ids.add(person)
            if decision == "REJECT":
                return {"status": "VISUAL_REVIEW_REJECTED", "proposal": expected}
            approved_roles.add(role)
            approved_keys.add(raw)
        verified = (
            approved_roles == {"primary", "independent"}
            and len(approved_keys) >= 2 and len(reviewer_ids) >= 2
        )
        return {
            "status": (
                "CELL_VISUAL_DUAL_VERIFIED" if verified
                else "SECOND_INDEPENDENT_REVIEW_PENDING"
            ),
            "proposal": expected,
            "reviewer_count": len(reviewer_ids),
            "legal_year_approved": False,
            "payment_approved": False,
        }
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        return {"status": "CELL_REVIEW_HOLD", "reason": type(exc).__name__, "proposal": None}



def render_review_overlay(selected: str | None) -> str:
    """Show authentic page ROI: amber if proposed, yellow only if dual signed."""
    from html import escape

    if not isinstance(selected, str) or selected.count(":") != 1:
        return "<p>HOLD — EK-20 hücre kimliği seçilmedi.</p>"
    row, field = selected.split(":")
    result = verdict(row, field)
    status, proposal = result.get("status"), result.get("proposal")
    if not isinstance(proposal, dict):
        return (
            '<p><strong>HOLD — Seçilen EK-20 hücresinin kaynak piksel ROI '
            'haritası henüz doğrulanmadı.</strong> '
            f'Durum: <code>{escape(str(status))}</code>. '
            "Sarı işaretleme üretilmez; özgün tablo yukarıda görülebilir.</p>"
        )
    try:
        from PIL import ImageDraw
        context = _original_context(row, field)
        if prepare_roi(row, field, proposal["pixel_bbox"]) != proposal:
            raise ValueError("Source changed since review")
        verified = status == "CELL_VISUAL_DUAL_VERIFIED"
        image = context["image"].copy().convert("RGBA")
        rect = proposal["pixel_bbox"]
        pen = ImageDraw.Draw(image, "RGBA")
        if verified:
            # A digitally signed visual transcription, not legal applicability.
            pen.rectangle(rect, fill=(255, 221, 0, 80), outline=(255, 195, 0, 255), width=5)
        else:
            pen.rectangle(rect, outline=(217, 119, 6, 255), width=5)
        out = io.BytesIO()
        image.convert("RGB").save(out, format="PNG")
        encoded = base64.b64encode(out.getvalue()).decode("ascii")
        content_label = (
            "İKİ BAĞIMSIZ GÖRSEL İNCELEME İMZASI DOĞRULANDI"
            if verified else "HOLD — GÖRSEL HÜCRE ADAYI; İKİNCİ İNCELEME BEKLENİYOR"
        )
        visual_class = "sarı" if verified else "turuncu"
        return (
            '<section style="border:1px solid #cbd5e1;padding:14px;background:white">'
            f'<strong>{escape(content_label)}</strong>'
            f'<p>İşaret rengi: {visual_class}. ROI yalnız özgün PDF SHA ve '
            "görüntü piksellerinden yeniden doğrulandı. "
            "Bu işlem mevzuatın ilgili yılda yürürlükte olduğunu, hak edişi "
            "veya tutarın ödenebilirliğini kanıtlamaz: hukukî/ödeme HOLD.</p>"
            f'<p>EK-20 satırı: <code>{escape(row)}</code>; sütun: '
            f'<code>{escape(field)}</code>; sayfa: 1; DPI: {DPI}; '
            f'koordinatlar: <code>{escape(str(rect))}</code></p>'
            f'<img src="data:image/png;base64,{encoded}" '
            'style="width:100%;height:auto;max-width:1100px" '
            'alt="Özgün sayfa piksellerinde ROI inceleme çerçevesi"/>'
            f'<p>Özgün SHA-256: <code>{escape(context["sha"])}</code>; '
            f'ROI RGB SHA-256: <code>{escape(proposal["roi_rgb_sha256"])}</code></p>'
            f'<p><a href="{escape(context["record"].official_url, quote=True)}" '
            'rel="noopener noreferrer" target="_blank">'
            'Özgün resmî PDF sayfasını aç ↗</a></p>'
            "<p>Sarı alan iki ayrı yetkili anahtarın görsel içerik ve konum "
            "beyanını gösterir; resmî PDF dosyası değiştirilmez. "
            "Çiftçi olguları, yıl-mevzuat bağı ve ödeme yetkisi HOLD.</p>"
            "</section>"
        )
    except (OSError, ValueError, KeyError, RuntimeError, ImportError, TypeError):
        return "<p>HOLD — Kaynak piksel hücresi yeniden doğrulanamadı.</p>"

def _write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create forbids quietly replacing a signed review/proposal.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def _cli_propose(args: argparse.Namespace) -> int:
    proposal = prepare_roi(args.row_id, args.field, list(args.bbox))
    path = _proposal_path(proposal["source_sha256"], args.row_id, args.field)
    _write_new(path, proposal)
    print(json.dumps({"path": str(path), "status": "ROI_PROPOSED_UNREVIEWED"},
                     ensure_ascii=False))
    return 0


def _cli_sign(args: argparse.Namespace) -> int:
    if not args.visual_confirmation:
        raise ValueError("Explicit personal visual confirmation is required")
    draft = _read_json(args.proposal)
    row, field = draft.get("row_id"), draft.get("field")
    context = prepare_roi(row, field, draft.get("pixel_bbox"))
    if draft != context or args.proposal.resolve() != _proposal_path(
        context["source_sha256"], row, field,
    ).resolve():
        raise ValueError("The signed ROI proposal is not the current original")
    trusted = _trusted_reviewers()
    if args.reviewer_id not in trusted:
        raise ValueError("Unknown reviewer")
    role, trusted_pub, trusted_raw = trusted[args.reviewer_id]
    with args.private_key.open("rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    if not isinstance(key, Ed25519PrivateKey) or key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    ) != trusted_raw:
        raise ValueError("Private key is not paired with the registered reviewer")
    # This command signs the reviewer's attestation, not a legal payout decision.
    signed = _review_payload(
        context, args.reviewer_id, role, args.decision,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    record = {
        "signed": signed,
        "signature_b64": base64.b64encode(key.sign(canonical(signed))).decode("ascii"),
    }
    path = _review_dir(context["source_sha256"], row, field) / (
        args.reviewer_id + ".json"
    )
    _write_new(path, record)
    print(json.dumps({"path": str(path), "status": "SIGNED_VISUAL_REVIEW_ONLY"},
                     ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="EK-20 source-pixel review: no payout approval")
    sub = parser.add_subparsers(dest="command", required=True)
    propose = sub.add_parser("propose")
    propose.add_argument("--row-id", required=True)
    propose.add_argument("--field", choices=FIELD_IDS, required=True)
    propose.add_argument("--bbox", type=int, nargs=4, required=True)
    sign = sub.add_parser("sign")
    sign.add_argument("--proposal", type=Path, required=True)
    sign.add_argument("--reviewer-id", required=True)
    sign.add_argument("--private-key", type=Path, required=True)
    sign.add_argument("--decision", choices=("APPROVE", "REJECT"), required=True)
    sign.add_argument("--visual-confirmation", action="store_true", required=True)
    args = parser.parse_args()
    try:
        return _cli_propose(args) if args.command == "propose" else _cli_sign(args)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
