<!--
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme ve inceleme.
-->

# P0-10.4 — Original EK-20 visual evidence + legal-source change chain (as of 2026-10-09)

**Status:** visually inspected primary EK-20 page, targeted legal source discovery expanded, exhaustive official archive and independent legal review still **HOLD**.

## Original EK-20 inspection

Verified original official attachment: https://resmigazete.gov.tr/eskiler/2025/12/20251230-9-1.pdf
SHA-256 (original byte archive, P0-10.3): `6984c901775212e0500148cbbb2d87ea34ad3783e10d6c798fa9ca320bf06a79`; 695,625 bytes. **One raster/image-only PDF page, no selectable text** (confirmed by direct MuPDF inspection of original byte artifact). The page is visibly headed `EK-20`, title `2026 YILI BİTKİSEL ÜRETİMDE BİYOLOJİK VE/VEYA BİYOTEKNİK MÜCADELE DESTEĞİ ÜRÜN-ETMEN VE DESTEK BİRİM TUTARLARI`.

From the actual rendered original image:
- Covered/KOBÜKS package: **4,650 TL/da** = biological 3,800 + pheromone/trap 850.
- Open-field package: **1,550 TL/da** = biological 700 + pheromone/trap 850.
- 12 rows visually transcribed in `configs/p0_10_4_ek20_visual_transcription.json`: covered vegetable group, citrus, open-field tomatoes, apple, vineyard, olives, apricot, pomegranate, quince, pear, peach, nectarine.
- A hyphen in the source is represented by `null`, **never zero**. Separate standalone biotechnical amount vs pheromone+trap vs only-pheromone must not be conflated.
- This is a **visual transcription pending independent expert verification**, not validated payment data; original PDF checksum binding and image-page number must match. No activation.

## Missing or changed legal instruments found

The previous five-source snapshot did **not** include:
- **Tebliğ 2025/13** — 5 Aug 2025, RG 32977, 2024/39 amendment. Article 4 says effective upon publication **but applicable from 1 Jan 2025**. It also changes EK-25 Arpa warehouse start from 1 June to 15 May. Original: https://www.resmigazete.gov.tr/eskiler/2025/08/20250805-4.htm ; corroboration: https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2025-2027%20Destekleme%20Tebli%C4%9Fi%20De%C4%9Fi%C5%9Fikli%C4%9Fi.pdf
- **Presidential Decision 10394** — 14 Sep 2025, RG 33017, original PDF https://www.resmigazete.gov.tr/eskiler/2025/09/20250914-6.pdf, amends 8859, effective 1 Jan 2026; preserves earlier provisions for 2025 production claims under its transition clause. Ministry announcement: https://www.tarimorman.gov.tr/HHGM/Haber/175/2025-2027-Yillarinda-Yapilacak-Bitkisel-Uretime-Yonelik-Desteklemeler-Ile-Diger-Bazi-Tarimsal-Desteklemelere-Iliskin-Kararda-Degisiklik-Yapilmasina-Dair-Karar-Yayimlanmistir
- **Presidential Decision 11781** — 8 Sep 2026, RG 33364, original PDF https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf, amends 8859. Art.6: parts of Art.1 effective on publication with retroactive validity from **1 Jan 2026**, Art.4 effective on publication with retroactive validity from **1 Jan 2025**, other provisions effective **1 Jan 2027**. Ministry: https://www.tarimorman.gov.tr/HHGM/Haber/262/2025-2027-Yillarinda-Yapilacak-Bitkisel-Uretime-Yonelik-Desteklemeler-Ile-Diger-Bazi-Tarimsal-Desteklemelere-Iliskin-Kararda-Degisiklik-Yapilmasina-Dair-Karar

The base 2024/39 **MADDE 21** expressly repeals 2022/32, 2022/34, and 2023/48. These earlier originals and their transitional cases still need preservation. P0-10.1 and P0-10.2 already captured 8859, 2024/39 and 2025/42, and P0-10.3 pinned original byte hashes for their two linked appendices.

## Explicit FAIL-CLOSED legal applicability assessment

`scripts/p0_10_4_temporal_audit.py` enforces that 2025/13, 10394, 2025/42 and 11781 cannot be omitted; that 2025 retroactive and transitional treatment is visible; that 11781 Art.1/Art.4 special dates are **not** falsely collapsed into a single effective date; that all three 2024/39 repeal targets exist as references; that a targeted web search cannot set `complete_official_coverage_proven=true`.

The full 2025–2027 official Gazette + Ministry day-index inventories, all related instruments, subsequent repeals/amendments, annex rows and date-specific consolidated rules are **not proven complete**. As of October 2026, full 2027 future amendment coverage cannot be guaranteed. Final release requires documented search scope/recall against official annual archive indices plus independent legal expert and original document hash signoff.

**Never activate payable decisions based on these visual/manual/targeted findings.** Evidence archive and screenshots are supplementary; legal source review and WORM storage remain separate.
