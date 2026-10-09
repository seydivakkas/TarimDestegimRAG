<!--
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme ve inceleme.
-->

# P0-10.1 — Real Official-Source Capture Corpus (RED-regression gate)

**Status:** source capture fixtures staged; **byte-exact HTTP origin and legal coverage not accepted**. Target: `feat/p0-10-1-official-source-fixtures`, not `main`. This does not supersede P0-9 Draft PR #28.

## Captured authority and immutable replay

| ID | Official URL | Gazette metadata | Material |
|---|---|---|---|
| 8859 | https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf | 2024-08-29, 32647 | Official PDF rendered into third-party HTML, **not** original PDF bytes |
| 2024/39 | https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm | 2024-12-31, 32769, fifth duplicate issue | Third-party HTML page capture |
| 2025/42 | https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm | 2025-12-30, 33123 | Third-party HTML page capture; amendment of 2024/39, effective 2026-01-01 |

`backend/tests/fixtures/p0_10_official/manifest.json` stores capture format, UTF-8 byte count, **captured representation SHA-256** and expected actual Gazette metadata. `original_source_sha256` is deliberately **null** in every entry because origin HTTP/PDF bytes were not available in the engineering environment. Treating a transformed HTML SHA as an official PDF SHA would be a provenance violation.

Three immutable HTML capture blobs are stored alongside the manifest to enable offline CI replays. This is a *frozen genuine-source-content corpus*, NOT an archive of verified original HTTP response bytes. The independent original-byte acquisition, annex attachments, issued/subsequent amendments, access timestamps, and full-year coverage remain **OPEN**.

## Regression contract

`backend/tests/integration/test_p0_10_1_real_official_corpus.py` verifies:
- The capture SHA-256 and size, document source URL, origin-SHA explicitly absent and legal publication disabled.
- Positive detection of 8859 as Presidential Decision and 2025/42 as amendment.
- **Strict expected failures** tagged `P010-A01` / `A02` / `A03` / `A05` / `A07`: real 2024/39 misclassification from its 8859 reference, base-vs-own number collision, mükerrer Gazette amendment reference, nontrivial publication vs effective dates, and annex page-hash misrepresentation.
- Strict `xfail` means **XPASS causes CI failure**. After correcting each implementation defect, remove its `xfail` marker and assert it as a regular passing regression. A green `pytest` run with XFAIL results is **not** permission to activate legislation or payment.

## Reproduction

Run `python -m pytest backend/tests/integration/test_p0_10_1_real_official_corpus.py -q --no-cov -rx` with project `.[dev,pdf-evidence]` dependencies. No live network needed during replay. Inspect `-rx` markers to see concrete current-parser deficiencies. NEVER infer full recall from these three pinned documents.

### Follow-up: origin-byte acquisition (not yet completed)

Fetch each original directly from the official domain using a controlled HTTPS client with explicit allowlist, TLS validation, bounded payload size and MIME/magic checks; save exact response bytes, calculate original SHA-256, verify independent official date/issue against trusted records, and freeze file digest under a new manifest revision. For 8859, retain original PDF and render/display it; for 2024/39 and 2025/42 retain original HTML bytes *before* any parser/browser conversion. Acquire linked EK-20 and earlier/repealed annex originals too. Until then `COVERAGE_INCOMPLETE` and `REVIEW/HOLD` remain mandatory.

Historical acceptance audit: https://github.com/seydivakkas/TarimDestegimRAG/issues/29
