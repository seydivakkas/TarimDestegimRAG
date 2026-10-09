"""Dinamik Kural Kataloğu Kalıcı Deposu (P0-11).

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.

YASAKLAR:
  1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
  2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
  3. Alt lisanslanamaz, satılamaz veya devredilemez.
  4. Tersine mühendislik yapılamaz.

İZİN VERİLEN KULLANIM:
  - GitHub üzerinde görüntüleme ve okuma.
  - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
İzin talepleri için: GitHub @seydivakkas
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tarim_destek_rag.rules.bitemporal_engine import BitemporalRuleCatalog


class DynamicRuleRepository:
    """Sentezlenen dinamik kuralların disk üzerindeki JSON kataloğunu yöneten depo."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        if base_dir is None:
            self.base_dir = Path("data/legal_update_archive/rules_catalog")
        else:
            self.base_dir = Path(base_dir) / "rules_catalog" if not str(base_dir).endswith("rules_catalog") else Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _year_path(self, year: int) -> Path:
        return self.base_dir / f"rules_{year}.json"

    def save_rules(self, year: int, rules: list[dict[str, Any]]) -> Path:
        """Belirli bir üretim yılına ait kuralları atomik olarak kaydeder."""
        target = self._year_path(year)
        tmp = target.with_suffix(".tmp")
        data = {
            "schema_version": 1,
            "production_year": year,
            "rule_count": len(rules),
            "rules": rules,
        }
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(target)
        return target

    def load_rules(self, year: int) -> list[dict[str, Any]]:
        """Belirli bir üretim yılının kurallarını yükler."""
        target = self._year_path(year)
        if not target.is_file():
            return []
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return data.get("rules", [])
        except Exception:
            return []

    def list_years(self) -> list[int]:
        """Katalogda kayıtlı olan üretim yıllarını listeler."""
        years = []
        for p in self.base_dir.glob("rules_*.json"):
            stem = p.stem.replace("rules_", "")
            if stem.isdigit():
                years.append(int(stem))
        return sorted(years)

    def get_catalog(self, years: list[int] | None = None) -> BitemporalRuleCatalog:
        """Kayıtlı kuralları BitemporalRuleCatalog motoruna yükler."""
        target_years = years or self.list_years()
        all_rules: list[dict[str, Any]] = []
        for y in target_years:
            all_rules.extend(self.load_rules(y))
        return BitemporalRuleCatalog.from_candidates(all_rules)

    def list_rules(
        self,
        year: int | None = None,
        program_key: str | None = None,
        crop_code: str | None = None,
        review_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Kuralları filtrelere göre listeler."""
        years_to_scan = [year] if year else self.list_years()
        results: list[dict[str, Any]] = []

        for y in years_to_scan:
            for rule in self.load_rules(y):
                if program_key and rule.get("program_key") != program_key:
                    continue
                if crop_code and rule.get("crop_code") != crop_code:
                    continue
                if review_status and rule.get("review_status") != review_status:
                    continue
                results.append(rule)

        return results
