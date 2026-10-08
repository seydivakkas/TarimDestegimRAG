# TarımDestekRAG — Yeniden Üretim ve Kurulum Rehberi (Reproduction)

> **Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)**  
> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**

---

## 1. Gereksinimler

- Windows 10/11 x64
- Python 3.11+ (veya `uv` paket yöneticisi)
- Flutter SDK (mobil istemciyi derlemek için opsiyonel)

---

## 2. Hızlı Kurulum

### Adım 1: Depoyu Hazırlama ve Sanal Ortam
```powershell
# Bağımlılıkları uv ile yükleme
uv sync
```

### Adım 2: Veritabanını Başlatma ve Tohumlama
```powershell
.venv\Scripts\python.exe -c "
from tarim_destek_rag.database.connection import init_db, SessionLocal
from tarim_destek_rag.normalization.seed_data import seed_2026_support_data
init_db()
s = SessionLocal()
seed_2026_support_data(s)
s.close()
print('Veritabanı hazırlandı!')
"
```

---

## 3. Çalıştırma

### A. Masaüstü & Web Paneli (Tek Tıkla Başlatma)
Klasör içindeki `baslat_pc.bat` dosyasına çift tıklayabilir veya terminalden çalıştırabilirsiniz:
```powershell
.venv\Scripts\python.exe run_pc.py
```
- **FastAPI Backend:** `http://127.0.0.1:8000/docs`
- **Gradio Web Paneli:** `http://127.0.0.1:7860`

---

## 4. Test ve Doğrulama Paketleri

### Bütün Testleri Çalıştırma:
```powershell
.venv\Scripts\pytest.exe -v
```

### 100 Vakalı Kapsamlı Benchmark v1:
```powershell
.venv\Scripts\python.exe -m tarim_destek_rag.evaluation.benchmark_runner_v1
```
Sonuçlar otomatik olarak:
- `benchmark/results.csv`
- `benchmark/report.md`
dosyalarına aktarılır.

### TD-P12 Arama (Retrieval) Karşılaştırma Testi:
```powershell
.venv\Scripts\python.exe -m tarim_destek_rag.evaluation.retrieval_benchmark
```
BM25, Dense ve Hibrit motorların Hit@1, Hit@3, Hit@5 ve MRR metriklerini canlı ölçer.
