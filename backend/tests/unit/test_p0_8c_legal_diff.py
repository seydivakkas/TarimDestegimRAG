"""Only exact-text, source-bound future-year changes; NO inferred repeal."""

import pytest
from tarim_destek_rag.auto_updater.legal_diff import LegalClause, compare_clause_sets

SHA_2029 = "a" * 64
SHA_2030 = "b" * 64


def clause(key, year, text, evidence_id):
    return LegalClause(
        key=key, document_sha256=SHA_2029 if year == 2029 else SHA_2030,
        page=4, exact_text=text, evidence_id=evidence_id,
        production_year=year, source_id=f"RG-SYNTH-{year}",
    )


def test_2030_amount_change_source_and_literal_coordinates_preserved():
    old = clause("Madde 6 / 2", 2029,
                 "Synthetic base support is 100,00 TL/da for category test.", 1)
    new = clause("Madde 6 / 2", 2030,
                 "Synthetic base support is 125,00 TL/da for category test.", 2)
    report = compare_clause_sets(
        previous_year=2029, target_year=2030, previous=[old], current=[new],
    )
    assert report["summary"]["TEXT_CHANGED"] == 1
    assert report["changes"][0]["current"]["document_sha256"] == SHA_2030
    assert report["changes"][0]["current"]["page"] == 4
    assert report["changes"][0]["numeric_change_needs_review"]
    assert report["changes"][0]["old_tl_mentions"][0]["decimal"] == "100.00"
    assert report["changes"][0]["new_tl_mentions"][0]["decimal"] == "125.00"
    assert report["legal_status"] == "REVIEW_REQUIRED"
    assert report["publication_activated"] is False
    assert report["complete_legal_search_proven"] is False
    assert len(report["report_sha256"]) == 64
    again = compare_clause_sets(
        previous_year=2029, target_year=2030, previous=[old], current=[new],
    )
    assert again["report_sha256"] == report["report_sha256"]


def test_removed_article_is_not_automatically_declared_repealed():
    unchanged_old = clause("Madde 3", 2029, "Synthetic conditions remain defined here.", 1)
    removed_old = clause("Madde 9", 2029, "Synthetic exception from 2029 legislation.", 2)
    new = clause("Madde 3", 2030, "Synthetic conditions remain defined here.", 3)
    report = compare_clause_sets(
        previous_year=2029, target_year=2030,
        previous=[unchanged_old, removed_old], current=[new],
        prior_complete=True, current_complete=True,
    )
    assert report["summary"] == {
        "TEXT_ADDED": 0, "TEXT_REMOVED": 1,
        "TEXT_CHANGED": 0, "TEXT_UNCHANGED": 1,
    }
    removal = next(c for c in report["changes"] if c["change_type"] == "TEXT_REMOVED")
    assert removal["repeal_effect_confirmed"] is False
    assert removal["human_legal_review_required"] is True
    assert report["complete_legal_search_proven"] is False


def test_explicit_repeal_phrase_only_flags_review():
    prev = clause("Madde 6", 2029, "Synthetic drip irrigation exception exists here.", 1)
    curr = clause(
        "Madde 6", 2030,
        "Synthetic clause: previous exception yürürlükten kaldırılmıştır.", 2,
    )
    report = compare_clause_sets(
        previous_year=2029, target_year=2030, previous=[prev], current=[curr],
    )
    change = report["changes"][0]
    assert change["repeal_language_detected"] is True
    assert change["repeal_effect_confirmed"] is False
    assert change["effective_from"] is None


def test_duplicate_article_or_wrong_year_is_rejected():
    old = clause("Madde 6", 2029, "Synthetic 2029 legal clause appears only once.", 1)
    new = clause("Madde 6", 2030, "Synthetic 2030 amendment is different from 2029.", 2)
    with pytest.raises(ValueError, match="duplicate"):
        compare_clause_sets(
            previous_year=2029, target_year=2030,
            previous=[old, old], current=[new],
        )
    with pytest.raises(ValueError, match="another production year"):
        compare_clause_sets(
            previous_year=2029, target_year=2030,
            previous=[new], current=[old],
        )


def test_no_false_completion_with_empty_selected_clause_list():
    row = clause("Madde 2", 2030, "Synthetic 2030 paragraph must be in original PDF.", 1)
    with pytest.raises(ValueError, match="No source-validated"):
        compare_clause_sets(
            previous_year=2029, target_year=2030,
            previous=[], current=[row],
        )
