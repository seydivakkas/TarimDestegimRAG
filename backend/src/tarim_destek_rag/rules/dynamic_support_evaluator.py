"""Çoklu Destek Kalemleri Dinamik Değerlendirme ve Fiyatlandırma Motoru (P0-11).

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

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from tarim_destek_rag.rules.bitemporal_engine import (
    BitemporalEvaluationResult,
    BitemporalRuleCatalog,
)
from tarim_destek_rag.rules.table_parser import normalize_crop_code

PROGRAM_NAMES = {
    "BASIC_SUPPORT": "Temel Destek",
    "PLANNED_PRODUCTION": "Planlı Üretim Desteği",
    "WATER_RESTRICTION": "Su Kısıtı İlave Desteği",
    "CERTIFIED_SEED": "Sertifikalı Tohum Kullanım Desteği",
    "CERTIFIED_SAPLING": "Sertifikalı Fidan Kullanım Desteği",
}


@dataclass(frozen=True)
class EvaluatedSupportItem:
    """Tek bir destek programına ait dinamik değerlendirme çıktısı."""

    program_key: str
    program_name: str
    status: str  # "ELIGIBLE", "NOT_ELIGIBLE", "REVIEW", "UNKNOWN"
    unit_amount: Decimal | None
    area_da: Decimal
    proposed_amount: Decimal | None
    payable_amount: Decimal | None
    reason: str
    rule_checks: tuple[str, ...] = ()
    source_document_sha256: str | None = None
    source_sentence_id: int | None = None
    effective_from: str | None = None
    effective_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.unit_amount is not None:
            d["unit_amount"] = str(self.unit_amount)
        if self.area_da is not None:
            d["area_da"] = str(self.area_da)
        if self.proposed_amount is not None:
            d["proposed_amount"] = str(self.proposed_amount)
        if self.payable_amount is not None:
            d["payable_amount"] = str(self.payable_amount)
        return d


@dataclass(frozen=True)
class MultiSupportEvaluationSummary:
    """Çiftçi parselinin tüm destek programları bazında toplu değerlendirme özeti."""

    production_year: int
    as_of_date: str
    crop_code: str
    area_da: Decimal
    province: str
    district: str
    overall_status: str  # "ELIGIBLE", "REVIEW", "NOT_ELIGIBLE"
    total_proposed_amount: Decimal | None
    total_payable_amount: Decimal | None
    items: list[EvaluatedSupportItem] = field(default_factory=list)
    fail_closed_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "production_year": self.production_year,
            "as_of_date": self.as_of_date,
            "crop_code": self.crop_code,
            "area_da": str(self.area_da),
            "province": self.province,
            "district": self.district,
            "overall_status": self.overall_status,
            "total_proposed_amount": (
                str(self.total_proposed_amount) if self.total_proposed_amount is not None else None
            ),
            "total_payable_amount": (
                str(self.total_payable_amount) if self.total_payable_amount is not None else None
            ),
            "fail_closed_reason": self.fail_closed_reason,
            "items": [it.to_dict() for it in self.items],
        }


class DynamicSupportEvaluator:
    """Çoklu tarımsal destek kalemlerini bitemporal deklaratif kurallarla hesaplayan motor."""

    @classmethod
    def evaluate_parcel(
        cls,
        *,
        catalog: BitemporalRuleCatalog,
        production_year: int,
        as_of_date: date,
        crop: str,
        area_da: Decimal,
        province: str,
        district: str,
        cks_registered: bool = True,
        irrigation: bool = False,
        certified_seed: bool = False,
        certified_sapling: bool = False,
        approval_verified: bool = False,
    ) -> MultiSupportEvaluationSummary:
        """Çiftçi ve parsel parametrelerini tüm destek programları üzerinden değerlendirir."""
        crop_code = normalize_crop_code(crop)
        facts = {
            "cks_registered": cks_registered,
            "crop_code": crop_code,
            "province": province.upper(),
            "district": district.upper(),
            "irrigation": irrigation,
            "certified_seed": certified_seed,
            "certified_sapling": certified_sapling,
        }

        # İlgili programlar listesi
        programs_to_eval = [
            "BASIC_SUPPORT",
            "PLANNED_PRODUCTION",
            "WATER_RESTRICTION",
            "CERTIFIED_SEED",
            "CERTIFIED_SAPLING",
        ]

        evaluated_items: list[EvaluatedSupportItem] = []
        any_draft_rule = False
        any_eligible = False
        any_review = False
        any_unknown = False

        for prog in programs_to_eval:
            prog_name = PROGRAM_NAMES.get(prog, prog)
            res: BitemporalEvaluationResult = catalog.evaluate(
                program_key=prog,
                crop_code=crop_code,
                production_year=production_year,
                as_of_date=as_of_date,
                facts=facts,
                province=province.upper(),
                district=district.upper(),
                approval_verified=approval_verified,
            )

            unit_amt = res.proposed_unit_amount
            prop_amt: Decimal | None = None
            pay_amt: Decimal | None = None

            if res.status == "ELIGIBLE":
                any_eligible = True
                if unit_amt is not None and area_da > 0:
                    prop_amt = (unit_amt * area_da).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                # Resmî onay kontrolü (VERIFIED ise ödeme oluşabilir, değilse None)
                if res.payable_amount is not None and area_da > 0:
                    pay_amt = (res.payable_amount * area_da).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                else:
                    any_draft_rule = True
                    pay_amt = None
            elif res.status == "REVIEW":
                any_review = True
                any_draft_rule = True
                if unit_amt is not None and area_da > 0:
                    prop_amt = (unit_amt * area_da).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                pay_amt = None
            elif res.status == "NOT_ELIGIBLE":
                prop_amt = Decimal("0.00")
                pay_amt = Decimal("0.00")
            elif res.status == "UNKNOWN":
                # An uncovered programme is unknown, NOT an entitlement of 0 TL.
                any_unknown = True
                pay_amt = None

            evaluated_items.append(
                EvaluatedSupportItem(
                    program_key=prog,
                    program_name=prog_name,
                    status=res.status,
                    unit_amount=unit_amt,
                    area_da=area_da,
                    proposed_amount=prop_amt,
                    payable_amount=pay_amt,
                    reason=res.reason,
                    rule_checks=res.rule_checks,
                    source_document_sha256=res.source_document_sha256,
                    source_sentence_id=res.source_sentence_id,
                    effective_from=res.effective_from,
                    effective_to=res.effective_to,
                )
            )

        # Toplam önerilen tutar (bilgilendirici simülasyon)
        valid_proposed = [
            it.proposed_amount for it in evaluated_items
            if it.status in ("ELIGIBLE", "REVIEW") and it.proposed_amount is not None
        ]
        total_proposed = sum(valid_proposed) if valid_proposed else Decimal("0.00")

        # Toplam yasal ödenebilir tutar (fail-closed güvenlik kuralı)
        total_payable: Decimal | None = None
        fail_closed_reason = None

        if any_draft_rule or any_review or any_unknown or not approval_verified:
            total_payable = None
            fail_closed_reason = (
                "Kuralların doğrulanmış aktivasyonu, tam program kapsamı veya incelemesi eksik (Fail-Closed). "
                "İmza, kaynak ve yürürlük kapısı geçilmeden hak ediş tutarı oluşturulamaz."
            )
        elif any_eligible:
            total_payable = sum(
                it.payable_amount for it in evaluated_items
                if it.status == "ELIGIBLE" and it.payable_amount is not None
            )
        else:
            total_payable = Decimal("0.00")

        # Genel durum
        if any_review or (any_unknown and any_eligible):
            overall_status = "REVIEW"
        elif any_unknown:
            overall_status = "UNKNOWN"
        elif any_eligible:
            overall_status = "ELIGIBLE"
        else:
            overall_status = "NOT_ELIGIBLE"

        return MultiSupportEvaluationSummary(
            production_year=production_year,
            as_of_date=as_of_date.isoformat(),
            crop_code=crop_code,
            area_da=area_da,
            province=province.upper(),
            district=district.upper(),
            overall_status=overall_status,
            total_proposed_amount=total_proposed,
            total_payable_amount=total_payable,
            items=evaluated_items,
            fail_closed_reason=fail_closed_reason,
        )
