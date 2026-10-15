"""G37 offline source importer for the previously recorded GitHub Actions originals.

Accepts a ZIP artifact (e.g. G37 verified HTML pack or full archived CI
artifact). This DOES NOT download a source from the current network and does
not establish later versions. Import only manifest-pinned original bytes
with exact SHA-256, length and safe, deterministic path.

Never mark legal-year, independent visual-review, farmer or payment PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

PILOT_IDS = frozenset({
    "RG_COMMUNIQUE_2024_39",
    "RG_AMENDMENT_2025_42",
})


def _store(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError("Source archive already has conflicting original bytes")


def import_originals(
    artifact: Path, *, manifest_file: Path, archive: Path,
    all_pinned: bool = False,
) -> list[dict]:
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Invalid source manifest")
    records = []
    with zipfile.ZipFile(artifact) as z:
        if len(z.infolist()) > 25:
            raise ValueError("Oversized ZIP entry count")
        for source in manifest.get("sources", []):
            if not isinstance(source, dict):
                continue
            if not all_pinned and source.get("id") not in PILOT_IDS:
                continue
            sha = source.get("original_sha256")
            suffix = ".pdf" if source.get("format") == "pdf" else ".html"
            if not isinstance(sha, str) or len(sha) != 64:
                raise ValueError("Invalid expected SHA")
            basename = "originals/" + sha + suffix
            try:
                entry = z.getinfo(basename)
            except KeyError:
                raise ValueError("Expected original missing: " + source["id"])
            maximum = 12_000_000 if suffix == ".pdf" else 3_000_000
            if (not 1 <= entry.file_size <= maximum
                    or entry.file_size != source.get("original_bytes")):
                raise ValueError("Archived original length does not match manifest")
            raw = z.read(entry)
            if hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError("Archived original SHA mismatch: " + source["id"])
            if suffix == ".pdf" and not raw.startswith(b"%PDF-"):
                raise ValueError("Archived file lacks PDF magic")
            if suffix == ".html" and b"<" not in raw[:4096]:
                raise ValueError("Archived file lacks HTML markers")
            dest = archive / "originals" / (sha + suffix)
            _store(dest, raw)
            records.append({
                "source_id": source["id"],
                "sha256": sha,
                "bytes": len(raw),
                "relative_path": "originals/" + sha + suffix,
                "source_status": "ORIGINAL_ARCHIVE_SHA_VERIFIED",
                "legal_year_status": "HOLD",
                "payment_status": "HOLD",
            })
    if not records:
        raise ValueError("No original source in the selected import scope")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Import SHA-pinned CI originals without network")
    parser.add_argument("artifact_zip", type=Path)
    parser.add_argument("--manifest", type=Path,
                        default=Path("configs/p0_10_3_original_source_manifest.json"))
    parser.add_argument("--archive", type=Path,
                        default=Path("data/legal_update_archive"))
    parser.add_argument("--all-pinned", action="store_true")
    args = parser.parse_args()
    try:
        items = import_originals(
            args.artifact_zip, manifest_file=args.manifest,
            archive=args.archive, all_pinned=args.all_pinned,
        )
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status":"IMPORT_HOLD", "reason":str(exc)[:250]},
                         ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": "ORIGINAL_BYTES_IMPORTED_NOT_LEGAL_PASS",
        "source_records": items,
        "source_location_review": "REQUIRED_ONCE_IMPORTED",
        "independent_legal_review": "HOLD",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
