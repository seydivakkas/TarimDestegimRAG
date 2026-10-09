# P0-10.3 — Original Gazette Byte Evidence, Linked Annexes and Year Coverage

**Current phase:** initial live collection / manifest pinning. **Full legal coverage:** HOLD.

This package follows [P0-10.2 PR #31](https://github.com/seydivakkas/TarimDestegimRAG/pull/31) and uses the frozen *third-party capture* corpus from [P0-10.1 PR #30](https://github.com/seydivakkas/TarimDestegimRAG/pull/30) **without rewriting or pretending those HTML representations are original source bytes**.

## Required primary sources and linked attachments

| ID | Original official URL | Relationship |
|---|---|---|
| 8859 | https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf | 29 Aug 2024, Gazette 32647 — base Presidential Decision |
| 2024/39 | https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm | 31 Dec 2024, Gazette 32769 fifth duplicate — base Communiqué |
| 2024/39 annex | https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8-1.pdf | Independent PDF URL linked by the preceding official HTML |
| 2025/42 | https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm | 30 Dec 2025, Gazette 33123 — amends 2024/39; effective 1 Jan 2026 |
| 2025/42 annex | https://resmigazete.gov.tr/eskiler/2025/12/20251230-9-1.pdf | Independent PDF linked by 2025/42 HTML; EK-20 reference requires a PDF-text/layout check |

Authoritative pinned original byte digests belong in `configs/p0_10_3_original_source_manifest.json` under `original_sha256`. **Until a successful direct HTTPS fetch, these MUST remain null.** Captured/rendered HTML hashes from P0-10.1 are **never copied into this manifest**.

## Two-stage source authentication

1. **COLLECT:** `python scripts/p0_10_3_source_integrity.py --mode collect --out data/p0_10_3_live_originals` downloads official HTTPS bodies directly (valid TLS, identity-encoding, no redirects, exact approved domains, bounded reads). Checks HTML/PDF structure, parent HTML attachment URL presence, SHA-256 and immutable digest-addressed original byte archives. Reports a machine-readable `report.json` and per-source `ORIGINAL_SOURCE` lines with actual byte hashes. The repository CI stores the whole output as a 90-day evidence artifact; that artifact is not permanent WORM retention.
2. **VERIFY (required for final original-byte acceptance):** A human checks independent official references and pins all actual original SHA-256 values in a reviewed manifest commit; run with `--mode verify`. **Any absent/changed digest, missing attachment, invalid PDF or unreachable source produces HOLD.** Use versioned snapshots and permanent WORM store for final archival signoff.

The current workflow performs the initial COLLECT step, **not final byte-pin VERIFY**. A green COLLECT is not a signed or complete legal evidence chain. **Do not set `complete_official_coverage_proven=true`** simply because all five direct URLs return successfully.

## Year scope and correctness

`assess_year_coverage()` emits explicit per-year results for 2025, 2026 and 2027. A successful fetch does not prove nationwide official law discovery completeness. The baseline 8859/2024/39 apply to the 2025–2027 framework; the 2025/42 amendment begins in 2026. The amendment preserves the previous version for 2025-origin transactions, requiring review of the relevant transition. The 2024/39 general effective date is 2025-01-01 with Article 10 exception 2025-05-01. Full-date applicability needs an amendment/repeal graph, Gazette archive index coverage and independent legal review.

**Strict requirements for P0-10 package acceptance:**
- Direct original source and annex bytes pinned by digest and replayed independently.
- Linked EK-20 verified from independently archived original PDF, with OCR/table content where necessary (a PDF containing a mention alone is not sufficient table verification).
- Official portal archive/date-window discovery evaluated for missing and amended items, not just a five-document manifest.
- Tamper, missing/changed/unreachable source and erroneous applicability tests all fail closed.
- Separate legal reviewer acceptance, WORM retention and production/payout approval.

**P0-10 full official completeness / legal activation is HOLD regardless of partial collection results.**
