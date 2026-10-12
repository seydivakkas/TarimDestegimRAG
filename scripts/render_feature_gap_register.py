"""Render the F01-F14 issue ledger from configs/feature_gap_register.json.

For feature-first planning only. Never treats OCR, code presence or a reviewer
work item as regulatory/production/payment approval or an F14 test pass.

Usage (from repository root):
  python scripts/render_feature_gap_register.py --write
  python scripts/render_feature_gap_register.py --check
  python scripts/render_feature_gap_register.py --stdout
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs" / "feature_gap_register.json"
OUTPUT = ROOT / "docs" / "OPEN_FEATURE_GAPS.md"
STATUSES = {
    "OPEN", "CODE_IN_PROGRESS", "BLOCKED_EXTERNAL",
    "DEFERRED_F14", "CLOSED_IMPLEMENTED",
}


def verify_register(source: dict) -> None:
    if source.get("schema_version") != 1:
        raise ValueError("Unknown register schema")
    features = source.get("features")
    items = source.get("work_items")
    if not isinstance(features, list) or len(features) != 14:
        raise ValueError("Exactly fourteen feature headings required")
    names = {f["id"] for f in features}
    if names != {f"F{x:02d}" for x in range(1, 15)}:
        raise ValueError("Missing or duplicate F01-F14 feature")
    if not isinstance(items, list) or len(items) > 300:
        raise ValueError("Invalid issue count")
    ids = [item["gap_id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate issue ID")
    for row in items:
        if (row["feature_id"] not in names
                or row["status"] not in STATUSES
                or row["priority"] not in ("P0", "P1", "P2", "P3")
                or any(not isinstance(row[key], str) or not row[key].strip()
                       for key in (
                           "title", "solution", "definition_of_done",
                           "responsible_role",
                       ))):
            raise ValueError("Incomplete or invalid issue entry")


def _cell(x: object) -> str:
    return " ".join(str(x).split()).replace("|", r"\|")


def render(data: dict) -> str:
    verify_register(data)
    features = data["features"]
    issues = data["work_items"]
    open_items = [x for x in issues if x["status"] != "CLOSED_IMPLEMENTED"]
    status = Counter(x["status"] for x in issues)
    lines = [
        "# Açık Mühendislik Eksikleri ve Çözüm Takip Listesi", "",
        f"**Son değerlendirme:** {data['last_reviewed']} — Kod envanteri, PR #41. "
        "Gerçek Windows/GPU, bağımsız hukukî kabul ve 48 EK-20 insan onayı "
        "bu tarihte yapılmış sayılmaz.",
        "",
        "**Tek kaynak:** configs/feature_gap_register.json. "
        "Bu okunabilir sayfa aynı veriden oluşturulmuştur. Yeniden üretmek "
        "için scripts/render_feature_gap_register.py --write.",
        "",
        f"**Toplam açık iş:** {len(open_items)} • "
        + " / ".join(f"{name}: {count}" for name, count in status.items())
        + ". Bunlar iş kalemidir; 48 EK-20 hücresi G05/G17'de ayrı izlenir.",
        "", "## F01–F14 özellik düzeyi", "",
        "| Paket | Özellik | Mevcut geliştirme durumu |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {_cell(f['id'])} | {_cell(f['title'])} | {_cell(f['status'])} |"
        for f in features
    )
    lines.extend([
        "", "## Tek tek açık işler: eksik → çözüm → kapanış", "",
        "| ID | Öncelik | Paket | Durum | Açık iş / problem | "
        "Yapacağımız çözüm | Kapanış kriteri |",
        "|---|---|---|---|---|---|---|",
    ])
    lines.extend(
        f"| {_cell(x['gap_id'])} | {_cell(x['priority'])} | "
        f"{_cell(x['feature_id'])} | {_cell(x['status'])} | "
        f"{_cell(x['title'])} | {_cell(x['solution'])} | "
        f"{_cell(x['definition_of_done'])} |"
        for x in issues
    )
    lines.extend([
        "", "## Mühendislik sırası / bağımlılıklar", "",
        "1. Kaynak gerçekliği: G01 → G05 ve G12/G14. SHA olmayan özgün "
        "dosyadan koordinat veya madde üretme.",
        "2. EK-20: G05 gerçek 48 ROI → G17 iki kişinin ayrı incelemesi "
        "→ G19 iptal güvenliği. Eksik onay HOLD.",
        "3. Navigasyon: G09 HTML metin düğümü → G10 PDF kaynak/ROI "
        "→ G11 tek gezgin → G20 Neden/SSS/rapor/mobil.",
        "4. Yıl geçerliliği: G12 tekil şartlar + G14 değişiklik grafiği "
        "→ G15 2025/2026/2027 → G16 EK-20 izolasyonu.",
        "5. Ürün: G22/G23 Windows/lisans, G24/G25 güncelleme, "
        "G26/G27 ödeme ayrımı → G28–G30 son F14.",
        "",
        "Durum kodları: OPEN (özellik açığı), CODE_IN_PROGRESS (kodlanıyor), "
        "BLOCKED_EXTERNAL (gerçek kaynak, insan veya donanım), "
        "DEFERRED_F14 (son kabulde), CLOSED_IMPLEMENTED "
        "(özellik kodu kapandı, F14 hukukî/teknik PASS değil).",
        "",
        "**PR politikası:** #41 DRAFT/unmerged, main değiştirilmez. "
        "Sarı görsel doğrulama, yürürlük ve ödeme onayı birbirinden ayrıdır.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--stdout", action="store_true")
    args = parser.parse_args()
    doc = render(json.loads(REGISTRY.read_text(encoding="utf-8")))
    if args.stdout:
        print(doc, end="")
    elif args.write:
        OUTPUT.write_text(doc, encoding="utf-8")
        print(f"Updated {OUTPUT}")
    elif not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != doc:
        print("Stale generated document: run --write")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
