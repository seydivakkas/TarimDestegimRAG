<!--
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme ve inceleme.
-->

# P0-10.3 — Original Gazette Byte Evidence, Linked Annexes and Year Coverage

**Current phase:** five byte-exact original HTTP/PDF SHA-256 digests pinned and independently replayed. **EK-20 table semantics and full legal-year coverage: HOLD.**

This package follows [P0-10.2 PR #31](https://github.com/seydivakkas/TarimDestegimRAG/pull/31) and uses the frozen *third-party capture* corpus from [P0-10.1 PR #30](https://github.com/seydivakkas/TarimDestegimRAG/pull/30) **without rewriting or pretending those HTML representations are original source bytes**.

## Required primary sources and linked attachments

| ID | Original official URL | Relationship |
|---|---|---|
| 8859 | https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf | 29 Aug 2024, Gazette 32647 — base Presidential Decision |
| 2024/39 | https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm | 31 Dec 2024, Gazette 32769 fifth duplicate — base Communiqué |
| 2024/39 annex | https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8-1.pdf | Independent PDF URL linked by the preceding official HTML |
| 2025/42 | https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm | 30 Dec 2025, Gazette 33123 — amends 2024/39; effective 1 Jan 2026 |
| 2025/42 annex | https://resmigazete.gov.tr/eskiler/2025/12/20251230-9-1.pdf | Independent PDF linked by 2025/42 HTML; EK-20 reference requires a PDF-text/layout check |

Authoritative pinned original byte digests belong in `configs/p0_10_3_original_source_manifest.json` under `original_sha256`. **All five SHA-256 values are now pinned to actual direct official HTTPS entity bytes**, corroborated by GitHub Actions run IDs `37906860240` and `37906865615`. The third-party capture hashes from P0-10.1 were **not** copied into this manifest.

## Two-stage source authentication

1. **COLLECT:** `python scripts/p0_10_3_source_integrity.py --mode collect --out data/p0_10_3_live_originals` downloads official HTTPS bodies directly (valid TLS, identity-encoding, no redirects, exact approved domains, bounded reads). Checks HTML/PDF structure, parent HTML attachment URL presence, SHA-256 and immutable digest-addressed original byte archives. Reports a machine-readable `report.json` and per-source `ORIGINAL_SOURCE` lines with actual byte hashes. The repository CI stores the whole output as a 90-day evidence artifact; that artifact is not permanent WORM retention.
2. **VERIFY (required for final original-byte acceptance):** A human checks independent official references and pins all actual original SHA-256 values in a reviewed manifest commit; run with `--mode verify`. **Any absent/changed digest, missing attachment, invalid PDF or unreachable source produces HOLD.** Use versioned snapshots and permanent WORM store for final archival signoff.

The workflow now performs direct `--mode verify --byte-contract-only`: this allows a *source-byte integrity* PASS only if all five direct official URLs produce exactly the pinned bytes and the HTML parents link to the expected PDF annexes. The report deliberately outputs `source_status=HOLD`, `annex_table_semantics_status=HOLD`, and `year_scope_completeness=NOT_PROVEN` when the EK-20 table cannot be reliably extracted. Byte-contract PASS is not legal acceptance, complete legal inventory, or an institutionally signed evidence chain. **Do not set `complete_official_coverage_proven=true`** simply because all five direct URLs return successfully.

## Year scope and correctness

`assess_year_coverage()` emits explicit per-year results for 2025, 2026 and 2027. A successful fetch does not prove nationwide official law discovery completeness. The baseline 8859/2024/39 apply to the 2025–2027 framework; the 2025/42 amendment begins in 2026. The amendment preserves the previous version for 2025-origin transactions, requiring review of the relevant transition. The 2024/39 general effective date is 2025-01-01 with Article 10 exception 2025-05-01. Full-date applicability needs an amendment/repeal graph, Gazette archive index coverage and independent legal review.

**Strict requirements for P0-10 package acceptance:**
- Direct original source and annex bytes pinned by digest and replayed independently.
- Linked EK-20 verified from independently archived original PDF, with OCR/table content where necessary (a PDF containing a mention alone is not sufficient table verification).
- Official portal archive/date-window discovery evaluated for missing and amended items, not just a five-document manifest.
- Tamper, missing/changed/unreachable source and erroneous applicability tests all fail closed.
- Separate legal reviewer acceptance, WORM retention and production/payout approval.

**P0-10 full official completeness / legal activation is HOLD regardless of partial collection results.**

## Observed pinned actual original bytes (independent runs)

The following are SHA-256 of **direct official server HTTP entity bytes** (not Firecrawl captures). The first direct download and a separately started PR download returned identical hashes for all five. See source evidence runs [37906860240](https://github.com/seydivakkas/TarimDestegimRAG/actions/runs/37906860240) and [37906865615](https://github.com/seydivakkas/TarimDestegimRAG/actions/runs/37906865615).

| Source ID | Original byte count | SHA-256 |
|---|---:|---|
| RG_DECISION_8859 | 1,436,150 | `89df0b6222edb4eddf3d5f588a4007061458adec8d518e3fbdb86b46ae5ba85f` |
| RG_COMMUNIQUE_2024_39 | 236,810 | `efb1ebea650cf836155728b6bd3599b76a0fbee70d1a8e5c85f2af4792734530` |
| RG_COMMUNIQUE_2024_39_ANNEX | 3,084,837 | `3d290ad65a41d8c2cee49e50581c7eb0bb4a3c429af9e6191eaab4bf64d2eafe` |
| RG_AMENDMENT_2025_42 | 45,886 | `74a91122f52190cc4dd4322c1d7b6036466d5432f8f11577230151dba0119269` |
| RG_AMENDMENT_2025_42_ANNEX | 695,625 | `6984c901775212e0500148cbbb2d87ea34ad3783e10d6c798fa9ca320bf06a79` |

**Important:** The annex original is downloaded and verified by its own SHA-256. A pypdf text extraction of the 2025/42 annex did *not* confirm the literal `EK-20` marker, and the scanner explicitly records `ANNEX_SEMANTIC_CONTENT` HOLD. Rendering, layout/table interpretation and/or human review remain mandatory. Do not treat a matched PDF byte hash as verified annex table values.

All three audited production years (2025, 2026, 2027) deliberately remain `HOLD` because enumerated official archive indices, complete later amendment/repeal chain, and detailed year/transition review are unproven. GitHub Actions artifacts have a 90-day retention limit; durable WORM archival and human approval are separate tasks.
