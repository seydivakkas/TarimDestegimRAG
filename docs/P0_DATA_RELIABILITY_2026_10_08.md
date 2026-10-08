# P0 — Hesaplama Doğruluğu ve Veri Güvenilirliği (2026-10-08)

## Kapsam ve durum

**P0.1 kod paketi:** Uygulandı; **tam otomatik test koşusu yapılmadı**. Bu belge, gerçek mevzuat sertifikası veya üretime hazır olma beyanı değildir.

### Düzeltmeler

1. PC formunun API'ye gönderdiği geçersiz `is_irrigated` anahtarı `irrigation: DRY | IRRIGATED | UNKNOWN` enum alanına dönüştürüldü. Rapor üretimi de aynı eşlemeyi kullanır.
2. BÜGEM 2026 kategori katsayıları, Bakanlığın **08.09.2026** tarihli 367 TL/da değişikliğiyle birleştirilerek örnek tohum veri tabanındaki **13 fiyat kaydı** ve soru-cevap fiyat kataloğu düzeltildi.
3. Su kısıtı ilavesi için sulu tarım şartı eklendi. Su kısıtlı havzalarda dane mısır/patates için temel destek reddi uygulandı.
4. 100 benchmark vakasının 46 beklenen tutarı ve dört mısır ret durumu güncellendi; su kısıtı vakalarına sulama alanı açıkça eklendi. Bu vakalar bağımsız onaylı başvuru kararları değil, sürümlenmiş test senaryolarıdır.
5. Atıf kayıt/yıl bilgisi eşleşmesi yeterli belge-pasaj kanıtı olmadığından `INSUFFICIENT_EVIDENCE` kabul edilir. Kaynak sürümü doğrulaması olmadan `%100 güncellik` raporlanmaz.
6. Arayüzde sabit %100 benchmark kartları kaldırıldı. Eski `benchmark/report.md` geçersiz ilan edilerek yeniden test için ayrıldı.
7. Aynı RAG chunk'larının tekrar indekslenmesi engellendi.
8. Web taraması yapmayan SSS düğmesi “yerel seed” olarak yeniden adlandırıldı; doğrulanmamış SSS kayıtları otomatik `verified=True` olmaz.
9. İndirilen raporun bir devlet kurumu belgesi olmadığı açıkça belirtilir.

## 2026 katsayı ve fiyat kaynağı

- [BÜGEM 2026 destekleme birim fiyatları (katsayı ve ürün grupları)](https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2026%20Y%C4%B1l%C4%B1%20Destekleme%20Birim%20Fiyatlar%C4%B1.pdf)
- [Tarım ve Orman Bakanlığı — 08.09.2026 bitkisel destek katsayısı güncellemesi](https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi)
- 2026 eski katsayı **310,00**, yeni katsayı **367,00 TL/da**. BÜGEM tablo kategorilerinin katsayıları uygulanır.

| Kalem | Katsayı | Yeni birim TL/da | Kullanım |
| --- | ---: | ---: | --- |
| Buğday/Arpa temel | 1,30 | 477,10 | Parsel/ÇKS uygunluğu |
| Buğday/Arpa planlı | 1,30 | 477,10 | Havza/üretim planı uygunluğu |
| Pamuk temel | 2,25 | 825,75 | Ürün türü |
| Ayçiçeği/Fındık temel | 1,50 | 550,50 | Ürün türü |
| Buğday/Arpa sertifikalı tohum | 0,56 | 205,52 | Belge şartı |
| Sertifikalı meyve fidanı | 5,00 | 1.835,00 | Tür/bahçe şartı |
| Mercimek su kısıtı ilavesi | 0,80 | 293,60 | Resmî su kısıtı + **sulu tarım** şartı |

2026 koşullu buğday temel + planlı toplamı 954,20 TL/da'dır; Bakanlığın duyurusunda yuvarlatılmış **954 TL/da** ifadesi bulunur. Toplamı herkese otomatik ödeme olarak yorumlamayın.

## Mevcut güvenlik sınırları / tamamlanması gereken P0.2

- **Belge-pasaj kanıt zinciri:** PDF/HTML indirimi, hash, yürürlük tarihi, madde ve birebir pasaj eşlemesi; ardından gerçek `VERIFIED` kararı.
- **Tam havza kapsamı:** Seed verisi yalnız örnek ilçeler içeriyor. Eksik coğrafi kayıt “kesin ret” gibi yorumlanmamalı.
- **Başvuru dönemleri:** Bazı sabit takvim varsayımları ve başvuru belgeleri resmî başvuru kaynağından tek tek denetlenmeli.
- **Program koşulları:** Sertifikalı fidan için kapama bahçe/tür/alan, münavebe, tarla su kısıtı, üretim yılı ve diğer istisnalar tamamlanmalı.
- **SSS:** Statik ve toplanmış tüm ifadeler (özellikle mevzuat tutarları, süreler) kaynak bazında yeniden incelenmeli; mevcut statik içerik resmî alıntı sayılamaz.
- **Hak ediş:** Demo hesapları kesin kamu ödemesi değildir; kişisel kayıt doğrulaması ve Bakanlık başvuru sonuçları yoktur.
- **Test/CI:** Uygulamanın gerçek bağımlılıklarıyla tam test, benchmark ve kaynak doğrulama senaryoları bu ortamda çalıştırılmadı. Eski başarı/g gecikme rakamları yeni sürüme taşınmaz.

## Çalıştırma

Proje kök dizininde:

```bash
uv sync --extra dev
uv run pytest backend/tests/unit/test_p0_2026_data_reliability.py -q
uv run pytest backend/tests -q
uv run python -m tarim_destek_rag.evaluation.benchmark_runner_v1
```

Çalışma sonunda `benchmark/report.md` ve `benchmark/results.csv` çıktısını o koşunun commit SHA'sı, makine donanımı ve kaynak sürümüyle beraber arşivleyin; yalnız daha önce commit'lenmiş raporları yeni sürüm metrikleri gibi kullanmayın.

**Not:** Bu aşamada uygulamanın `main` dalına otomatik birleştirme yapılmamalıdır; bağımlılıklarla gerçek testler çalıştırıldıktan ve uzman mevzuat karşılaştırması yapıldıktan sonra incelenmelidir.
