"""Opt-in Baidu Unlimited-OCR over SHA-verified original Gazette page pixels.

OCR can suggest text/rows; it cannot create PDF locations, independent reviewer
signatures, normative source spans, legal-year PASS, or payment activation.
No OCR text is automatically imported into claim bindings or the EK-20 matrix.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path
from typing import Any

_DPI = 180
_MAX_OCR_PREVIEW = 8_000
_PAGE_RE = re.compile(r"([A-Z][A-Z0-9_]{2,79}):([1-9][0-9]{0,3})\Z")
_FIELD_RE = re.compile(r"([a-z][a-z0-9_]{1,60}):(biological_tl_da|biotechnical_tl_da|feromone_trap_tl_da|feromone_only_tl_da)\Z")


def engine_status() -> dict[str, Any]:
    """Availability is an explicit opt-in; never download weights at runtime."""
    if os.getenv("TARIM_RAG_UNLIMITED_OCR_ENABLED") != "1":
        return {"status": "OPT_IN_DISABLED"}
    if os.getenv("TARIM_RAG_UNLIMITED_OCR_TRUST_LOCAL_CODE") != "I_AUDITED_THE_LOCAL_MODEL_CODE":
        return {"status": "LOCAL_CUSTOM_CODE_APPROVAL_REQUIRED"}
    path = os.getenv("TARIM_RAG_UNLIMITED_OCR_MODEL_DIR", "")
    model = Path(path) if path else Path()
    if (not path or not model.is_absolute() or not model.is_dir()
            or not (model / "config.json").is_file()):
        return {"status": "OFFLINE_MODEL_DIRECTORY_MISSING"}
    python_path = os.getenv("TARIM_RAG_UNLIMITED_OCR_PYTHON", sys.executable)
    executable = Path(python_path)
    if not executable.is_absolute() or not executable.is_file():
        return {"status": "ISOLATED_PYTHON_NOT_CONFIGURED"}
    return {"status": "CONFIGURED_NOT_RUNTIME_VERIFIED",
            "model_dir": str(model.resolve()), "python": str(executable.resolve())}


def _verified_original_page(page_key: str) -> tuple[bytes, dict[str, Any]]:
    from tarim_destek_rag.citations.pdf_page_indexer import get_global_pdf_indexer

    if not isinstance(page_key, str):
        raise ValueError("Unselected source page")
    match = _PAGE_RE.fullmatch(page_key)
    if match is None:
        raise ValueError("Invalid source/page selector")
    doc_id, number = match.group(1), int(match.group(2))
    idx = get_global_pdf_indexer()
    record = idx.get_page(doc_id, number)
    if record is None:
        raise ValueError("Original source page not available")
    source, _ = idx._verified_pdf(doc_id)
    if (record.source_sha256 != source["original_sha256"]
            or record.official_url != source["url"] + f"#page={number}"):
        raise ValueError("Source identity is not SHA-pinned")
    png, marks, digest = idx.screenshot(record, dpi=_DPI)
    if marks or digest != source["original_sha256"]:
        raise ValueError("Unexpected source annotation or SHA change")
    return png, {
        "source_id": doc_id,
        "source_sha256": digest,
        "source_page": number,
        "source_url": record.official_url,
        "render_dpi": _DPI,
    }


def _pixel_values(*values: Any) -> list[int]:
    result = []
    for value in values:
        if type(value) not in (int, float) or isinstance(value, bool):
            raise ValueError("ROI requires integer pixel coordinates")
        iv = int(value)
        if value != iv:
            raise ValueError("ROI coordinates must be integers")
        result.append(iv)
    return result


def _compare_tesseract(png: bytes) -> str:
    executable = shutil.which("tesseract")
    if not executable:
        return "Tesseract kurulu değil; karşılaştırma yapılmadı."
    try:
        process = subprocess.run(
            [executable, "stdin", "stdout", "-l", "tur+eng"],
            input=png, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=90, check=False,
        )
        if process.returncode:
            return "Tesseract bu görüntü için çıktı üretemedi."
        return (process.stdout.decode("utf-8", errors="replace").strip()
                or "Tesseract bu bölgeyi boş okudu.")[:_MAX_OCR_PREVIEW]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return "Tesseract karşılaştırması başarısız."


def _run_local_model(png: bytes) -> tuple[str, str]:
    config = engine_status()
    if config["status"] != "CONFIGURED_NOT_RUNTIME_VERIFIED":
        return config["status"], ""
    if not png or len(png) > 25_000_000:
        return "ORIGINAL_IMAGE_OUT_OF_BOUNDS", ""
    try:
        with tempfile.TemporaryDirectory(prefix="tarim-unlimited-ocr-") as folder:
            root = Path(folder)
            image = root / "original_pixels.png"
            result_path = root / "result.json"
            image.write_bytes(png)
            try:
                image.chmod(0o600)
            except OSError:
                pass  # Windows: NTFS ACL policy must be applied externally.
            command = [
                config["python"],
                str(Path(__file__).with_name("unlimited_ocr_worker.py")),
                "--image", str(image),
                "--model-dir", config["model_dir"],
                "--result", str(result_path),
                "--output-dir", str(root / "model_output"),
            ]
            environment = os.environ.copy()
            environment.update({
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_DATASETS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
            })
            kwargs: dict[str, Any] = {}
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            execution = subprocess.run(
                command, env=environment, cwd=str(root),
                capture_output=True, check=False, timeout=900, **kwargs,
            )
            if execution.returncode != 0:
                # No logs leaked to GUI (paths or sensitive original text).
                return "UNLIMITED_OCR_WORKER_FAILED", ""
            if not result_path.is_file() or result_path.stat().st_size > 500_000:
                return "OCR_RESPONSE_MISSING_OR_OVERSIZED", ""
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            if (not isinstance(payload, dict)
                    or payload.get("schema_version") != 1
                    or payload.get("engine") != "baidu/Unlimited-OCR"
                    or payload.get("status") != "OCR_UNREVIEWED"
                    or not isinstance(payload.get("text"), str)
                    or not payload["text"].strip()):
                return "OCR_RESPONSE_UNTRUSTED", ""
            return "OCR_UNREVIEWED", payload["text"][:200_000]
    except (OSError, ValueError, TypeError, json.JSONDecodeError,
            subprocess.TimeoutExpired):
        return "UNLIMITED_OCR_NOT_AVAILABLE", ""


def _render_selected_page(
    page_key: str | None, *, selected_ek20: str | None = None,
    coords: list[int] | None = None, evaluation: dict[str, Any] | None = None,
) -> str:
    from PIL import Image

    try:
        png, source = _verified_original_page(page_key or "")
        image = Image.open(io.BytesIO(png)).convert("RGB")
        if not 0 < image.width * image.height <= 40_000_000:
            raise ValueError("Unreasonably large screenshot")
        if coords is not None:
            # EK-20 exists for this exact 2026 original/page ONLY. OCR does
            # not bind an arbitrary drawn rectangle to a legal cell.
            year = (evaluation.get("parcel") or {}).get("production_year") \
                if isinstance(evaluation, dict) else None
            if year != 2026 or not isinstance(selected_ek20, str):
                raise ValueError("EK-20 requires a current 2026 evaluation")
            match = _FIELD_RE.fullmatch(selected_ek20)
            if match is None:
                raise ValueError("Missing EK-20 semantic cell")
            if (source["source_id"] != "RG_AMENDMENT_2025_42_ANNEX"
                    or source["source_page"] != 1):
                raise ValueError("Wrong source document for EK-20")
            from tarim_destek_rag.citations.ek20_cell_provenance import (
                prepare_roi, _pixel_sha,
            )
            proposal = prepare_roi(match.group(1), match.group(2), coords)
            if (proposal["source_sha256"] != source["source_sha256"]
                    or proposal["image_size"] != [image.width, image.height]
                    or proposal["page_rgb_sha256"] != _pixel_sha(image)):
                raise ValueError("Original image/pixel proposal mismatch")
            image = image.crop(tuple(coords))
            if _pixel_sha(image) != proposal["roi_rgb_sha256"]:
                raise ValueError("ROI digest mismatch")
            source["roi_bbox_original_180dpi"] = coords
            source["roi_rgb_sha256"] = proposal["roi_rgb_sha256"]
            source["candidate_ek20_cell_id"] = selected_ek20
        out = io.BytesIO()
        image.save(out, format="PNG")
        crop_png = out.getvalue()
        candidate_sha = hashlib.sha256(crop_png).hexdigest()
        model_status, model_text = _run_local_model(crop_png)
        if model_status != "OCR_UNREVIEWED":
            return (
                "<section><strong>HOLD — Baidu Unlimited-OCR çalıştırılamadı.</strong>"
                f"<p>Durum: <code>{escape(model_status)}</code>. "
                "Model yalnız önceden kurulu ve yönetici tarafından incelenmiş "
                "yerel dosyalarla çalıştırılır; otomatik indirme yoktur.</p>"
                f"<p>Özgün kaynak: <code>{escape(source['source_id'])}</code> · "
                f"Sayfa {source['source_page']} · SHA-256 "
                f"<code>{escape(source['source_sha256'])}</code></p></section>"
            )
        tesseract_text = _compare_tesseract(crop_png)
        region = (
            f"<p>Özgün 180 DPI ROI: <code>{escape(str(coords))}</code> · "
            f"ROI RGB SHA-256: <code>{escape(source['roi_rgb_sha256'])}</code></p>"
            if coords is not None else "<p>Özgün 180 DPI sayfanın tamamı işlendi.</p>"
        )
        return (
            '<section style="padding:14px;border:1px solid #d97706;background:#fffbeb">'
            "<strong>HOLD — Baidu Unlimited-OCR görsel okuma taslağı</strong>"
            "<p>Bu çıktı metin tahminidir. PDF/hücre konumuna otomatik kanıt "
            "atamaz, mevzuat yürürlük veya ödeme onayı vermez. Sarı işaret yoktur.</p>"
            f"<p>Kaynak: <code>{escape(source['source_id'])}</code> · "
            f"Sayfa {source['source_page']} · OCR görüntüsü DPI {_DPI}</p>"
            f"<p>Özgün PDF SHA-256: <code>{escape(source['source_sha256'])}</code>"
            f" · İşlenen PNG SHA-256: <code>{escape(candidate_sha)}</code></p>"
            + region
            + "<h4>Baidu Unlimited-OCR (taslak)</h4>"
            + '<pre style="white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:10px">'
            + escape(model_text[:_MAX_OCR_PREVIEW]) + "</pre>"
            + "<h4>Tesseract karşılaştırması (taslak)</h4>"
            + '<pre style="white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:10px">'
            + escape(tesseract_text) + "</pre>"
            + "<p>Bu OCR çıktıları imzalı inceleme kaydı değildir. "
            "Görsel kaynak konumu ve iki bağımsız incelemeci onayı ayrı kalır.</p>"
            + "</section>"
        )
    except (OSError, ValueError, ImportError, KeyError, TypeError):
        return "<p>HOLD — Gerçek özgün sayfa, yıl veya ROI doğrulanamadı; OCR çalıştırılmadı.</p>"


def render_unlimited_ocr_page(page_key: str | None) -> str:
    """Only a verified selected original PDF page, never an uploaded surrogate."""
    return _render_selected_page(page_key)


def render_unlimited_ocr_ek20(
    selected_ek20: str | None,
    x0: Any, y0: Any, x1: Any, y1: Any,
    evaluation: dict[str, Any] | None,
) -> str:
    """Exact original-pixel selected EK20 crop, independent of legal approvals."""
    try:
        rect = _pixel_values(x0, y0, x1, y1)
        return _render_selected_page(
            "RG_AMENDMENT_2025_42_ANNEX:1",
            selected_ek20=selected_ek20, coords=rect,
            evaluation=evaluation,
        )
    except (TypeError, ValueError):
        return "<p>HOLD — Gerçek 180 DPI piksel ROI koordinatları seçilmedi.</p>"
