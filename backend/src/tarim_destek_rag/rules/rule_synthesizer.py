"""Dinamik Mevzuat ve Tablolardan Deklaratif Kural Sentezleyici (P0-11).

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

import re
from datetime import UTC, datetime
from typing import Any

from tarim_destek_rag.rules.bitemporal_engine import BitemporalRuleCatalog
from tarim_destek_rag.rules.table_parser import (
    ParsedAnnexMatrix,
    TableParser,
)
from tarim_destek_rag.updates.legislation_models import DiscoveredLegislation


def _ascii_slug(text: str) -> str:
    """Türkçe karakterleri ASCII eşdeğerlerine çevirir (Kural ID uyumluluğu için)."""
    tr_map = {
        "Ç": "C", "ç": "C", "Ğ": "G", "ğ": "G", "İ": "I", "ı": "I",
        "Ö": "O", "ö": "O", "Ş": "S", "ş": "S", "Ü": "U", "ü": "U",
    }
    res = "".join(tr_map.get(ch, ch) for ch in text)
    return re.sub(r"[^A-Z0-9_]", "_", res.upper()).strip("_")


class RuleSynthesizer:
    """Keşfedilen mevzuat ve ek tablolardan bitemporal deklaratif kuralları üreten sentezleyici."""

    @classmethod
    def synthesize_candidates(
        cls,
        discovered: DiscoveredLegislation,
        matrix: ParsedAnnexMatrix | None = None,
        production_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Mevzuat ve ek tablo matrislerinden doğrulanabilir kural adayı sözlükleri üretir."""
        year = (
            production_year
            or (discovered.effective_dates.valid_production_years[0]
                if discovered.effective_dates.valid_production_years else 2026)
        )

        effective_from = discovered.effective_dates.effective_date or f"{year}-01-01"
        effective_to = f"{year}-12-31"

        pub_at = (
            f"{discovered.identity.rg_date}T00:00:00Z"
            if discovered.identity.rg_date
            else f"{year - 1}-12-31T00:00:00Z"
        )
        disc_at = discovered.discovered_at_utc or datetime.now(UTC).isoformat()

        doc_sha = discovered.document_sha256
        if len(doc_sha) != 64:
            doc_sha = "0" * 64

        if matrix is None:
            pages = [""]
            matrix = TableParser.parse_annex_matrices(
                discovered.annex_tables, pages, production_year=year
            )

        candidates: list[dict[str, Any]] = []
        sentence_counter = 100

        # 1. TEMEL DESTEK KURALLARI (BASIC_SUPPORT)
        for r in matrix.rate_rows:
            sentence_counter += 1
            crop_ascii = _ascii_slug(r.crop_code)
            rule_id = f"RULE_{year}_BASIC_{crop_ascii}"[:90]

            cand = {
                "schema_version": 1,
                "rule_id": rule_id,
                "program_key": "BASIC_SUPPORT",
                "crop_code": r.crop_code,
                "production_year": year,
                "province": "*",
                "district": "*",
                "base_coefficient": str(r.base_coefficient),
                "category_multiplier": str(r.category_multiplier),
                "official_unit_amount": str(r.official_unit_amount),
                "unit": "TRY/da",
                "effective_from": effective_from,
                "effective_to": effective_to,
                "published_at": pub_at,
                "discovered_at": disc_at,
                "source_document_sha256": doc_sha,
                "source_sentence_id": sentence_counter,
                "conditions": {
                    "all_of": [
                        {"field": "cks_registered", "op": "eq", "value": True},
                        {"field": "crop_code", "op": "eq", "value": r.crop_code},
                    ]
                },
                "review_status": "DRAFT",
            }
            candidates.append(cand)

        # 2. PLANLI ÜRETİM DESTEK KURALLARI (PLANNED_PRODUCTION)
        for p in matrix.planned_rows:
            sentence_counter += 1
            crop_ascii = _ascii_slug(p.crop_code)
            rule_id = f"RULE_{year}_PLANNED_{crop_ascii}"[:90]

            cand = {
                "schema_version": 1,
                "rule_id": rule_id,
                "program_key": "PLANNED_PRODUCTION",
                "crop_code": p.crop_code,
                "production_year": year,
                "province": "*",
                "district": "*",
                "base_coefficient": str(p.base_coefficient),
                "category_multiplier": str(p.category_multiplier),
                "official_unit_amount": str(p.official_unit_amount),
                "unit": "TRY/da",
                "effective_from": effective_from,
                "effective_to": effective_to,
                "published_at": pub_at,
                "discovered_at": disc_at,
                "source_document_sha256": doc_sha,
                "source_sentence_id": sentence_counter,
                "conditions": {
                    "all_of": [
                        {"field": "cks_registered", "op": "eq", "value": True},
                        {"field": "crop_code", "op": "eq", "value": p.crop_code},
                    ]
                },
                "review_status": "DRAFT",
            }
            candidates.append(cand)

        # 3. SU KISITI HAVZA VE İLÇE KURALLARI (WATER_RESTRICTION)
        for w in matrix.water_rows:
            for dist in w.districts:
                for encouraged in w.encouraged_crops:
                    sentence_counter += 1
                    dist_ascii = _ascii_slug(dist)
                    crop_ascii = _ascii_slug(encouraged)
                    rule_id = f"RULE_{year}_WATER_{crop_ascii}_{dist_ascii}"[:90]

                    cand = {
                        "schema_version": 1,
                        "rule_id": rule_id,
                        "program_key": "WATER_RESTRICTION",
                        "crop_code": encouraged,
                        "production_year": year,
                        "province": w.province,
                        "district": dist,
                        "base_coefficient": str(w.unit_amount),
                        "category_multiplier": str(w.multiplier),
                        "official_unit_amount": str(w.unit_amount),
                        "unit": "TRY/da",
                        "effective_from": effective_from,
                        "effective_to": effective_to,
                        "published_at": pub_at,
                        "discovered_at": disc_at,
                        "source_document_sha256": doc_sha,
                        "source_sentence_id": sentence_counter,
                        "conditions": {
                            "all_of": [
                                {"field": "cks_registered", "op": "eq", "value": True},
                                {"field": "crop_code", "op": "eq", "value": encouraged},
                                {"field": "irrigation", "op": "eq", "value": False},
                            ]
                        },
                        "review_status": "DRAFT",
                    }
                    candidates.append(cand)

        # 4. SERTİFİKALI TOHUM KURALLARI (CERTIFIED_SEED)
        for s in matrix.seed_rows:
            sentence_counter += 1
            crop_ascii = _ascii_slug(s.crop_code)
            rule_id = f"RULE_{year}_SEED_{crop_ascii}"[:90]

            cand = {
                "schema_version": 1,
                "rule_id": rule_id,
                "program_key": "CERTIFIED_SEED",
                "crop_code": s.crop_code,
                "production_year": year,
                "province": "*",
                "district": "*",
                "base_coefficient": str(s.base_coefficient),
                "category_multiplier": str(s.multiplier),
                "official_unit_amount": str(s.unit_amount),
                "unit": "TRY/da",
                "effective_from": effective_from,
                "effective_to": effective_to,
                "published_at": pub_at,
                "discovered_at": disc_at,
                "source_document_sha256": doc_sha,
                "source_sentence_id": sentence_counter,
                "conditions": {
                    "all_of": [
                        {"field": "cks_registered", "op": "eq", "value": True},
                        {"field": "crop_code", "op": "eq", "value": s.crop_code},
                        {"field": "certified_seed", "op": "eq", "value": True},
                    ]
                },
                "review_status": "DRAFT",
            }
            candidates.append(cand)

        # 5. SERTİFİKALI FİDAN KURALLARI (CERTIFIED_SAPLING)
        for sp in matrix.sapling_rows:
            sentence_counter += 1
            crop_ascii = _ascii_slug(sp.crop_code)
            rule_id = f"RULE_{year}_SAPLING_{crop_ascii}"[:90]

            cand = {
                "schema_version": 1,
                "rule_id": rule_id,
                "program_key": "CERTIFIED_SAPLING",
                "crop_code": sp.crop_code,
                "production_year": year,
                "province": "*",
                "district": "*",
                "base_coefficient": str(sp.base_coefficient),
                "category_multiplier": str(sp.multiplier),
                "official_unit_amount": str(sp.unit_amount),
                "unit": "TRY/da",
                "effective_from": effective_from,
                "effective_to": effective_to,
                "published_at": pub_at,
                "discovered_at": disc_at,
                "source_document_sha256": doc_sha,
                "source_sentence_id": sentence_counter,
                "conditions": {
                    "all_of": [
                        {"field": "cks_registered", "op": "eq", "value": True},
                        {"field": "crop_code", "op": "eq", "value": sp.crop_code},
                        {"field": "certified_sapling", "op": "eq", "value": True},
                    ]
                },
                "review_status": "DRAFT",
            }
            candidates.append(cand)

        return candidates

    @classmethod
    def compile_bitemporal_catalog(
        cls,
        discovered: DiscoveredLegislation,
        matrix: ParsedAnnexMatrix | None = None,
        production_year: int | None = None,
    ) -> BitemporalRuleCatalog:
        """Sentezlenen kuralları derleyip doğrulanmış BitemporalRuleCatalog oluşturur."""
        candidates = cls.synthesize_candidates(
            discovered, matrix=matrix, production_year=production_year
        )
        return BitemporalRuleCatalog.from_candidates(candidates)
