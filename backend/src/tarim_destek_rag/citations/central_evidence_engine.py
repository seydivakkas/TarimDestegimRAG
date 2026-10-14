"""Authoritative evidence service for desktop, mobile API, reports and FAQ.

This layer is intentionally the ONLY public gateway for per-check normative
records. Delegates original SHA/span/ROI verification to the existing canonical
contract and original-source modules, never runs OCR independently and never
promotes a similarity hit into binding or legal/payment PASS.
"""
from __future__ import annotations

from typing import Any

from tarim_destek_rag.citations.check_identity import check_claim_id, extracted_checks
from tarim_destek_rag.citations.canonical_evidence_contract import (
    claim_contract, evaluation_contract, faq_contract,
    render_claim_contract_html, render_claim_coverage_html,
)


class CentralEvidenceEngine:
    """One evidence record, reused across PC, mobile, report and FAQ."""

    def for_claim(
        self, evaluation: dict[str, Any] | None, claim_id: str | None,
    ) -> dict[str, Any]:
        return claim_contract(evaluation, claim_id)

    def for_check(
        self, evaluation: dict[str, Any] | None, *,
        rule_id: str, support_id: str, check_id: str,
    ) -> dict[str, Any]:
        """Resolve ONLY one emitted check within the current evaluation."""
        try:
            uid = check_claim_id(rule_id, support_id, check_id)
        except (TypeError, ValueError):
            return self.for_claim(evaluation, None)
        matches = [
            row for row in extracted_checks(evaluation)
            if (row["id"] == uid and row["check_id"] == check_id
                and row["rule_id"] == rule_id
                and row["support_id"] == support_id
                and row["identity_status"] == "RULE_EMITTED_STABLE_CHECK_ID")
        ]
        if len(matches) != 1:
            return self.for_claim(evaluation, None)
        return self.for_claim(evaluation, uid)

    def for_evaluation(
        self, evaluation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return evaluation_contract(evaluation)

    def for_faq(
        self, faq: dict[str, Any] | None, *,
        evaluation: dict[str, Any] | None = None,
        exact_claim_id: str | None = None,
    ) -> dict[str, Any]:
        return faq_contract(
            faq, evaluation=evaluation, exact_claim_id=exact_claim_id,
        )

    def render_claim(
        self, evaluation: dict[str, Any] | None, claim_id: str | None,
    ) -> str:
        return render_claim_contract_html(evaluation, claim_id)

    def render_coverage(
        self, evaluation: dict[str, Any] | None,
    ) -> str:
        return render_claim_coverage_html(evaluation)

    def render_2026_cks_pilot(
        self, evaluation: dict[str, Any] | None,
    ) -> str:
        """Auditable single pilot: same check ID for PASS/FAIL/MISSING.

        A matching original HTML node may display an orange textual
        highlight, but legal effective-year and payment never go PASS.
        """
        from html import escape
        row = self.pilot_2026_cks(evaluation)
        if row.get("check_id") != "BASIC_CKS_REGISTRATION":
            return (
                "<section><strong>ÇKS pilotu: HOLD</strong>"
                "<p>2026 Temel Destek kuralının sabit ÇKS kontrolü "
                "henüz bu değerlendirmede bulunamadı. "
                "Kaynak veya oran uydurulmaz.</p></section>"
            )
        head = (
            '<section style="padding:12px;border:1px solid #cbd5e1">'
            '<h3>2026 Temel Destek — ÇKS uçtan uca kaynak pilotu</h3>'
            '<p><strong>check_id:</strong> BASIC_CKS_REGISTRATION · '
            f'<strong>claim_id:</strong> {escape(str(row["claim_id"]))}</p>'
            f'<p><strong>Güncel durum metni:</strong> '
            f'{escape(str(row.get("claim_text") or ""))}</p>'
            '<p><strong>Mevzuat yılı:</strong> 2026 için geçerlilik '
            'bağımsız tamamlanmadı: HOLD. '
            '<strong>Hak ediş:</strong> HOLD. '
            '<strong>Ödeme:</strong> HOLD.</p>'
        )
        return head + self.render_claim(evaluation, row["claim_id"]) + "</section>"

    def pilot_2026_cks(
        self, evaluation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Fixed semantic check and year scope; outcome wording irrelevant."""
        result = self.for_check(
            evaluation,
            rule_id="RULE_BASIC_SUPPORT_2026",
            support_id="BASIC_SUPPORT_2026",
            check_id="BASIC_CKS_REGISTRATION",
        )
        if result.get("production_year") != 2026:
            # No claimed law can be carried into another year.
            return self.for_claim(evaluation, None)
        return result


central_evidence_engine = CentralEvidenceEngine()
