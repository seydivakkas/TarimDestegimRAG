# TarımDestekRAG — Benchmark Durumu (P0 2026 Güncellemesi)

**Durum: Henüz bu sürümde yeniden çalıştırılmadı.**

Bu dosyadaki önceki **%100 karar, %100 atıf, %100 güncellik, %0 desteksiz iddia** ve gecikme değerleri mevcut P0 sürümünü temsil etmediği için kaldırılmıştır. Değişen katsayılar ve beklenen test çıktıları için yeni bir koşu gerekir.

Gerçek ortamda:

```bash
uv sync --extra dev
uv run pytest backend/tests -q
uv run python -m tarim_destek_rag.evaluation.benchmark_runner_v1
```

Koşucu bu dosyayı yalnızca yürütüldüğünde gerçek raporla değiştirecektir. Atıf pasaj doğrulaması ve kaynak sürüm güncelliği henüz uygulanmadığı için atıf/güncellik başarı garantisi verilmez.

2026 rakamları için kaynaklar:
- [BÜGEM 2026 birim fiyat katsayı cetveli](https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2026%20Y%C4%B1l%C4%B1%20Destekleme%20Birim%20Fiyatlar%C4%B1.pdf)
- [Bakanlık 8 Eylül 2026 katsayı güncellemesi](https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi)
