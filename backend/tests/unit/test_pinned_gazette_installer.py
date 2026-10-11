"""Original Gazette source importer tests: only pinned official bytes accepted."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf
import pytest

from scripts.install_pinned_gazette_sources import install_original


def _source(tmp_path: Path) -> tuple[dict, Path]:
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    digest = hashlib.sha256(data).hexdigest()
    import_dir = tmp_path / "imports"
    import_dir.mkdir()
    (import_dir / (digest + ".pdf")).write_bytes(data)
    return {
        "id": "SYNTHETIC_TEST_ONLY",
        "format": "pdf",
        "original_sha256": digest,
        "original_bytes": len(data),
        "url": "https://www.resmigazete.gov.tr/test-only.pdf",
    }, import_dir


def test_offline_exact_byte_import_and_no_replacement(tmp_path: Path) -> None:
    item, src = _source(tmp_path)
    root = tmp_path / "archive"
    result = install_original(item, archive_root=root, import_dir=src)
    assert result["status"] == "PINNED_BYTES_INSTALLED"
    assert install_original(item, archive_root=root, import_dir=src)[
        "status"
    ] == "ALREADY_PINNED"
    target = root / "originals" / (item["original_sha256"] + ".pdf")
    target.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="tampered"):
        install_original(item, archive_root=root, import_dir=src)


def test_wrong_original_hash_fails_closed(tmp_path: Path) -> None:
    item, src = _source(tmp_path)
    item["original_sha256"] = "a" * 64
    with pytest.raises(OSError):
        install_original(item, archive_root=tmp_path / "archive", import_dir=src)


def test_untrusted_url_and_format_rejected_without_io(tmp_path: Path) -> None:
    item, src = _source(tmp_path)
    item["url"] = "https://evil.test/source.pdf"
    with pytest.raises(ValueError, match="permitted official"):
        install_original(item, archive_root=tmp_path / "archive", import_dir=src)
    item["url"] = "https://www.resmigazete.gov.tr/official.pdf"
    item["format"] = "html"
    with pytest.raises(ValueError, match="manifest"):
        install_original(item, archive_root=tmp_path / "archive", import_dir=src)
