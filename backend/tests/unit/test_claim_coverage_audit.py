"""Only individual claim-to-span proofs can complete a justification audit."""
from __future__ import annotations

from tarim_destek_rag.citations.claim_coverage import audit_evaluation_claims


def test_article_link_does_not_falsely_verify_every_rule_claim():
    sha = "a" * 64
    data = {
        "rules": [{
            "support_id": "BASIC_SUPPORT_2026", "rule_id": "RULE_BASIC_SUPPORT_2026",
            "passed_checks": ["ÇKS kaydı aktif.", "Üretim yılı 2026."],
            "failed_checks": ["Parsel alanı hatalı."],
            "missing_fields": ["verified_support_rate"],
        }],
        "explanations": [{
            "support_id": "BASIC_SUPPORT_2026",
            "citations": [{
                "source_id": "RG_COMMUNIQUE_2024_39",
                "section": "MADDE 4 (1)", "snippet": "Resmî metin örneği",
                "document_sha256": sha,
                "verification_status": "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW",
                "highlighted_pdf_url": (
                    f"/evidence/highlight/html/{sha}?support_id=BASIC_SUPPORT_2026"
                    "#tarim-evidence-highlight"
                ),
            }],
        }],
    }
    audit = audit_evaluation_claims(data)
    assert audit["decision_claim_count"] == 4
    assert audit["located_source_count"] == 1
    assert audit["claim_level_verified_count"] == 0
    assert audit["unmatched_claim_count"] == 4
    assert audit["acceptance"] == "HOLD"
    assert all(x["highlighted_pdf_url"] is None for x in audit["claims"])
    assert {x["claim_type"] for x in audit["claims"]} == {
        "PASSED_CHECK", "FAILED_CHECK", "MISSING_FIELD",
    }


def test_unverified_source_does_not_add_a_provenance_entry():
    audit = audit_evaluation_claims({
        "rules": [{
            "support_id": "CERTIFIED_SEED_2026",
            "passed_checks": ["Tohum faturası beyan edildi."],
        }],
        "explanations": [{
            "support_id": "CERTIFIED_SEED_2026",
            "citations": [{
                "section": "MADDE 3",
                "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
                "snippet": "Tahmini mevzuat açıklaması",
            }],
        }],
    })
    assert audit["located_source_count"] == 0
    assert audit["unmatched_claim_count"] == 1
    assert audit["acceptance"] == "HOLD"


def test_empty_audit_is_not_false_pass():
    report = audit_evaluation_claims({"rules": [], "explanations": []})
    assert report["acceptance"] == "NO_CLAIMS_TO_AUDIT"
    assert report["claim_level_verified_count"] == 0
