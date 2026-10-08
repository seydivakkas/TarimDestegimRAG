import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session
from tarim_destek_rag.calculator.calculator import SupportCalculator
from tarim_destek_rag.database.repository import SupportRepository
from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, Parcel
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.orchestrator import DecisionOrchestrator


class BenchmarkCase(BaseModel):
    """Tek bir ground truth test vakası."""

    case_id: str
    category: str
    support_id: str
    province: str
    district: str
    crop: str
    area_da: Decimal
    cks_status: bool | None
    seed_certificate_available: bool | None = None
    sapling_certificate_available: bool | None = None
    production_year: int = 2026
    expected_status: EligibilityStatusEnum
    expected_amount: Decimal | None = None
    notes: str = ""


class BenchmarkMetrics(BaseModel):
    """Benchmark ölçüm sonuçları."""

    total_cases: int
    passed_cases: int
    failed_cases: int
    eligibility_accuracy: float
    calculation_accuracy: float
    failures: list[dict[str, Any]] = []


class DecisionBenchmarkRunner:
    """Master Plan TD-P10 deterministik karar motoru doğrulayıcısı."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.orchestrator = DecisionOrchestrator()
        self.support_repo = SupportRepository(session)

    def run_case(self, case: BenchmarkCase) -> tuple[bool, dict[str, Any]]:
        """Tek bir vakayı çalıştırır ve beklenen ile fiili sonucu karşılaştırır."""
        farmer = FarmerProfile(
            province=case.province,
            district=case.district,
            cks_status=case.cks_status,
        )
        parcel = Parcel(
            crop=case.crop,
            area_da=case.area_da,
            production_year=case.production_year,
            seed_certificate_available=case.seed_certificate_available,
            sapling_certificate_available=case.sapling_certificate_available,
        )

        results = self.orchestrator.evaluate_all(farmer, parcel, self.session)
        target_rule_res = next((r for r in results if r.support_id == case.support_id), None)

        if not target_rule_res:
            return False, {
                "case_id": case.case_id,
                "error": f"Kural sonucu bulunamadı: {case.support_id}",
            }

        status_ok = target_rule_res.status == case.expected_status

        # Tutar hesabı kontrolü
        amount_ok = True
        amt_record = self.support_repo.get_amount(case.support_id, parcel.crop)
        unit_amt = amt_record.unit_amount if amt_record else None
        calc_res = SupportCalculator.calculate(target_rule_res, parcel.area_da, unit_amt)

        if case.expected_amount is not None:
            amount_ok = calc_res.estimated_amount == case.expected_amount

        success = status_ok and amount_ok
        details = {
            "case_id": case.case_id,
            "category": case.category,
            "expected_status": case.expected_status,
            "actual_status": target_rule_res.status,
            "expected_amount": str(case.expected_amount) if case.expected_amount else None,
            "actual_amount": str(calc_res.estimated_amount) if calc_res.estimated_amount else None,
            "status_ok": status_ok,
            "amount_ok": amount_ok,
            "failed_checks": target_rule_res.failed_checks,
            "missing_fields": target_rule_res.missing_fields,
        }
        return success, details

    def run_suite(self, cases: list[BenchmarkCase]) -> BenchmarkMetrics:
        """Tüm vaka listesini çalıştırır ve metrikleri raporlar."""
        passed_count = 0
        status_correct_count = 0
        amount_correct_count = 0
        failures = []

        for c in cases:
            success, details = self.run_case(c)
            if success:
                passed_count += 1
            else:
                failures.append(details)

            if details["status_ok"]:
                status_correct_count += 1
            if details["amount_ok"]:
                amount_correct_count += 1

        total = len(cases)
        eligibility_acc = (status_correct_count / total) * 100 if total > 0 else 0.0
        calc_acc = (amount_correct_count / total) * 100 if total > 0 else 0.0

        metrics = BenchmarkMetrics(
            total_cases=total,
            passed_cases=passed_count,
            failed_cases=len(failures),
            eligibility_accuracy=round(eligibility_acc, 2),
            calculation_accuracy=round(calc_acc, 2),
            failures=failures,
        )
        logger.info(
            "Benchmark tamamlandı: %d/%d (%0.1f%%)",
            passed_count,
            total,
            eligibility_acc,
            extra={"component": "BenchmarkRunner"},
        )
        return metrics


def load_cases_from_jsonl(path: str = "data/benchmark/cases.jsonl") -> list[BenchmarkCase]:
    """JSONL dosyasından ground truth vakalarını yükler."""
    file_path = Path(path)
    if not file_path.exists():
        return []

    cases: list[BenchmarkCase] = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                cases.append(BenchmarkCase(**item))
    return cases
