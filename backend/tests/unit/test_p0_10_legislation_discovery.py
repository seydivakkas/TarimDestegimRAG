"""P0-10 Gerçek Resmî Mevzuat Keşif ve Yapısal Sınıflandırma Test Paketi.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app
from tarim_destek_rag.updates.discovery import (
    OfficialPortal,
    scan_official_sources,
)
from tarim_destek_rag.updates.legislation_analyzer import LegislationAnalyzer
from tarim_destek_rag.updates.legislation_models import (
    LegislationType,
    TableKind,
)
from tarim_destek_rag.updates.legislation_repository import LegislationCatalogRepository

# Örnek 2024/8859 Cumhurbaşkanı Kararı metni
SAMPLE_PRESIDENTIAL_DECISION = """
24 Ağustos 2024 TARİHLİ VE 32642 SAYILI RESMÎ GAZETE
CUMHURBAŞKANI KARARI
Karar Sayısı: 8859
Ekli "2025-2027 Yıllarında Yapılacak Bitkisel Üretime Destekleme Ödemelerine İlişkin Karar"ın yürürlüğe konulmasına karar verilmiştir.
MADDE 1 - (1) Bu Kararın amacı, 2025-2027 üretim yıllarında tarımsal üretimin planlanmasıdır.
MADDE 22 - (1) Bu Karar 1/1/2025 tarihinde yürürlüğe girer.
MADDE 23 - (1) Bu Karar hükümlerini Tarım ve Orman Bakanı yürütür.
"""

# Örnek 2024/39 Bakanlık Tebliği metni
SAMPLE_COMMUNIQUE_2024_39 = """
24 Ağustos 2024 TARİHLİ VE 32642 SAYILI RESMÎ GAZETE
Tarım ve Orman Bakanlığından:
BİTKİSEL ÜRETİME DESTEKLEME ÖDEMESİ YAPILMASINA DAİR TEBLİĞ
(TEBLİĞ NO: 2024/39)
BİRİNCİ BÖLÜM
MADDE 1 - Bu Tebliğin amacı, bitkisel üretim destekleme ödemelerinin usul ve esaslarını belirlemektir.
MADDE 6 - (1) Temel destek ödemesi EK-1'de yer alan katsayılar üzerinden hesaplanır.
(3) (a) Su kısıtı bulunan havzalarda kuru tarım yapan çiftçilere ilave destek verilir.
MADDE 18 - (1) Bu Tebliğ 1/1/2025 tarihinde yürürlüğe girer.
MADDE 19 - (1) Bu Tebliğ hükümlerini Tarım ve Orman Bakanı yürütür.

EK-1 TEMEL DESTEK KATSAYI TABLOSU
EK-2 PLANLI ÜRETİM DESTEKLEMESİ ÜRÜN LİSTESİ
EK-3 SU KISITI BULUNAN HAVZALAR VE İLÇELER LİSTESİ
"""

# Örnek 2025/42 Değişiklik Tebliği metni
SAMPLE_AMENDMENT_2025_42 = """
15 Eylül 2025 TARİHLİ VE 32900 SAYILI RESMÎ GAZETE
Tarım ve Orman Bakanlığından:
BİTKİSEL ÜRETİME DESTEKLEME ÖDEMESİ YAPILMASINA DAİR TEBLİĞDE
DEĞİŞİKLİK YAPILMASINA DAİR TEBLİĞ
(TEBLİĞ NO: 2025/42)
MADDE 1 - 24/8/2024 tarihli ve 32642 sayılı Resmî Gazete'de yayımlanan Bitkisel Üretime Destekleme Ödemesi Yapılmasına Dair Tebliğ (Tebliğ No: 2024/39)'in 6 ncı maddesinin üçüncü fıkrasının (a) bendi aşağıdaki şekilde değiştirilmiştir.
MADDE 2 - Aynı Tebliğin 16 ncı maddesi aşağıdaki şekilde değiştirilmiştir.
MADDE 3 - Aynı Tebliğin EK-3 listesine yeni ilçeler eklenmiştir.
MADDE 4 - Bu Tebliğ yayımı tarihinde yürürlüğe girer.
"""


def test_classify_legislation_types():
    assert LegislationAnalyzer.classify_type(SAMPLE_PRESIDENTIAL_DECISION) == LegislationType.CUMHURBASKANI_KARARI
    assert LegislationAnalyzer.classify_type(SAMPLE_COMMUNIQUE_2024_39) == LegislationType.BAKANLIK_TEBLIGI
    assert LegislationAnalyzer.classify_type(SAMPLE_AMENDMENT_2025_42) == LegislationType.DEGISIKLIK_TEBLIGI
    assert LegislationAnalyzer.classify_type("ÇİFTÇİ KAYIT SİSTEMİ YÖNETMELİĞİ") == LegislationType.YONETMELIK


def test_extract_identity_from_presidential_decision():
    ident = LegislationAnalyzer.extract_identity(SAMPLE_PRESIDENTIAL_DECISION)
    assert ident.legislation_type == LegislationType.CUMHURBASKANI_KARARI
    assert ident.number == "8859"
    assert ident.rg_date == "2024-08-24"
    assert ident.rg_number == "32642"
    assert ident.authority == "T.C. CUMHURBAŞKANLIĞI"


def test_extract_identity_from_communique():
    ident = LegislationAnalyzer.extract_identity(SAMPLE_COMMUNIQUE_2024_39)
    assert ident.legislation_type == LegislationType.BAKANLIK_TEBLIGI
    assert ident.number == "2024/39"
    assert ident.rg_date == "2024-08-24"
    assert ident.rg_number == "32642"
    assert ident.authority == "T.C. TARIM VE ORMAN BAKANLIĞI"


def test_extract_effective_dates_and_production_years():
    dates = LegislationAnalyzer.extract_effective_dates(SAMPLE_COMMUNIQUE_2024_39, default_rg_date="2024-08-24")
    assert dates.effective_date == "2025-01-01"
    assert "MADDE 18" in (dates.effective_clause_text or "")

    dates_pres = LegislationAnalyzer.extract_effective_dates(SAMPLE_PRESIDENTIAL_DECISION)
    assert dates_pres.effective_date == "2025-01-01"
    assert dates_pres.valid_production_years == [2025, 2026, 2027]


def test_extract_amendment_targets():
    amend = LegislationAnalyzer.extract_amendment_target(SAMPLE_AMENDMENT_2025_42)
    assert amend is not None
    assert amend.base_legislation_no == "2024/39"
    assert amend.base_rg_date == "2024-08-24"
    assert amend.base_rg_number == "32642"
    assert "MADDE 6" in amend.modified_articles
    assert "MADDE 16" in amend.modified_articles
    assert "EK-3" in amend.modified_articles


def test_extract_annex_tables():
    pages = [SAMPLE_COMMUNIQUE_2024_39]
    tables = LegislationAnalyzer.extract_annex_tables(pages)
    assert len(tables) >= 3
    codes = {t.annex_code for t in tables}
    assert "EK-1" in codes
    assert "EK-2" in codes
    assert "EK-3" in codes

    by_code = {t.annex_code: t for t in tables}
    assert by_code["EK-1"].table_kind == TableKind.SUPPORT_RATES
    assert by_code["EK-2"].table_kind == TableKind.PLANNED_PRODUCTION
    assert by_code["EK-3"].table_kind == TableKind.WATER_RESTRICTION


def test_legislation_catalog_repository(tmp_path):
    repo = LegislationCatalogRepository(tmp_path)
    analysis = LegislationAnalyzer.analyze_document(
        SAMPLE_COMMUNIQUE_2024_39.encode("utf-8"),
        source_url="https://www.resmigazete.gov.tr/eskiler/2024/08/20240824-1.htm",
        mime_type="text/html",
    )
    saved_path = repo.save(analysis)
    assert saved_path.is_file()

    loaded = repo.load(analysis.document_sha256)
    assert loaded is not None
    assert loaded.identity.number == "2024/39"
    assert loaded.effective_dates.effective_date == "2025-01-01"
    assert len(loaded.annex_tables) == len(analysis.annex_tables)

    all_items = repo.list_all()
    assert len(all_items) == 1
    assert all_items[0]["number"] == "2024/39"


def test_scan_official_sources_includes_legislation_analysis(tmp_path):
    portal = OfficialPortal(
        source_id="TEST_PORTAL",
        index_url="https://www.tarimorman.gov.tr/index",
        allowed_hosts=("www.tarimorman.gov.tr",),
    )
    doc_url = "https://www.tarimorman.gov.tr/2024-39.htm"

    def fetch(url, hosts):
        if url == portal.index_url:
            return (
                f'<a href="{doc_url}">2024/39 sayılı Bitkisel Üretim Tebliği</a>'.encode(),
                "text/html",
            )
        if url == doc_url:
            return SAMPLE_COMMUNIQUE_2024_39.encode("utf-8"), "text/html"
        raise ValueError("Unknown URL")

    result = scan_official_sources(
        production_year=2026,
        portals=[portal],
        output=tmp_path,
        fetch=fetch,
    )

    assert result["new_or_changed"] == 1
    doc = result["documents"][0]
    assert doc["legal_effective_from"] == "2025-01-01"
    assert doc["legislation_analysis"] is not None
    assert doc["legislation_analysis"]["legislation_type"] == "BAKANLIK_TEBLIGI"
    assert doc["legislation_analysis"]["number"] == "2024/39"
    assert doc["legislation_analysis"]["annex_tables_count"] >= 3
    assert doc["legal_status"] == "DRAFT_NEEDS_CLAUSE_AND_HUMAN_REVIEW"
    assert doc["verified_rates_imported"] is False


def test_api_legislation_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", "p0-10-test-key")
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(tmp_path))

    repo = LegislationCatalogRepository(tmp_path)
    analysis = LegislationAnalyzer.analyze_document(
        SAMPLE_COMMUNIQUE_2024_39.encode("utf-8"),
        source_url="https://www.resmigazete.gov.tr/2024-39.htm",
        mime_type="text/html",
    )
    repo.save(analysis)

    with TestClient(app) as client:
        # 1. Yetkisiz erişim 403 almalı
        res_unauth = client.get("/admin/legal-updates/legislation")
        assert res_unauth.status_code == 403

        # 2. Yetkili erişim mevzuat listesi
        headers = {"x-admin-key": "p0-10-test-key"}
        res = client.get("/admin/legal-updates/legislation", headers=headers)
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 1
        assert items[0]["number"] == "2024/39"

        # 3. Belge detay sorgulama
        sha = analysis.document_sha256
        res_detail = client.get(f"/admin/legal-updates/legislation/{sha}", headers=headers)
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["identity"]["number"] == "2024/39"
        assert len(detail["annex_tables"]) >= 3

        # 4. Anında metin analiz uç noktası
        raw_res = client.post(
            "/admin/legal-updates/analyze-raw",
            json={
                "source_url": "https://www.resmigazete.gov.tr/test-amend.htm",
                "text_or_base64": SAMPLE_AMENDMENT_2025_42,
                "mime_type": "text/html",
            },
            headers=headers,
        )
        assert raw_res.status_code == 200
        raw_data = raw_res.json()
        assert raw_data["identity"]["legislation_type"] == "DEGISIKLIK_TEBLIGI"
        assert raw_data["identity"]["number"] == "2025/42"
        assert raw_data["amendment_target"]["base_legislation_no"] == "2024/39"
