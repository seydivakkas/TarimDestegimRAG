# P0-10.2 — Real-source parser correction and verification gate

**Scope:** source-aware issuing-document classification, amendment self-number vs amended target, Gazette fifth-duplicate reference, explicit-only legal effective dates and article exceptions, and annex integrity semantics.

**Review branch:** `feat/p0-10-2-real-source-parser-fixes`, based on P0-10.1 corpus branch; no changes to `main`, payment approval, production release or P0-9.

## Real captured-source regression contracts

1. **CUMHURBASKANI_KARARI vs BAKANLIK_TEBLIGI:** Classify based on the issuing heading before `MADDE 1`; references to Presidential Decision 8859 in 2024/39 body are citations, not the document's type.
2. **Own number:** the actual 2025/42 title includes its predecessor `2024/39` first. Select the new document's heading number (`2025/42`); keep amended target (`2024/39`) separate.
3. **Amendment reference:** parse `31/12/2024 tarihli ve 32769 beşinci mükerrer sayılı Resmî Gazete’de ... (Tebliğ No: 2024/39)` rather than treating the first number as its own issue.
4. **Effective date:** `2025/42` effective `2026-01-01`, not publication `2025-12-30`; original `2024/39` `MADDE 22` gives general `2025-01-01` and exceptional `MADDE 10` `2025-05-01`. `EffectiveDateInfo.article_effective_dates` persists these exceptions through the JSON repository.
5. **No guessed legal effect:** an unmatched/missing effective clause yields `effective_date=None`, even if the publication date is known; only explicit `yayımı tarihinde` may use Gazette date.
6. **Annex original evidence:** a mention of EK-20 is **not** the linked annex file. `AnnexTableInfo.content_sha256=None` for unverified references; it must not be set to the parent HTML/PDF page-text hash. An independently fetched and validated annex must be added in a future provenance package.

## Tests

All six previously strict `xfail` assertions in `backend/tests/integration/test_p0_10_1_real_official_corpus.py` were converted to **ordinary required passing tests**, using unchanged P0-10.1 captured representations. Extra regression cases cover actual Gazette header date/issue, unknown legal effect vs publication date, and an explicit publication-date clause.

The original 3 captured HTML representations and their frozen SHA-256 hashes are **unchanged**. They are **not** the byte-identical source HTTP/PDF archive: P0-10 independent original-byte acquisition and the attachment content of EK-20 remain pending. No test suite can infer full legal discovery recall from this three-document corpus.

## Mandatory acceptance

- Exact HEAD Ruff, compileall, all backend tests, and independent CI check workflows pass.
- **Six converted regressions must show actual PASS**, not `xfail`, skip, or `XPASS`.
- Existing synthetic unit, year-neutral and legal-gate tests remain green; no payable amount, legal signature or production activation changes.
- P0-10 full acceptance stays **HOLD** pending byte-exact origin source, annex original, exhaustive portal recall and independent legal review.

Audit tracking: https://github.com/seydivakkas/TarimDestegimRAG/issues/29
Corpus PR dependency: https://github.com/seydivakkas/TarimDestegimRAG/pull/30
