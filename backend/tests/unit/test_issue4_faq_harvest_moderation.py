"""Issue #4: Resmî Kaynak Taraması, SSS Doğrulama, Provenans ve Moderasyon Hattı Testleri.

Kapsam:
- SourceRegistry & URLAllowlist: İzinli resmî alan adları, HTTPS zorunluluğu, SSRF/özel IP koruması.
- HTML Parser & Extraction: En az iki resmî fixture (BÜGEM SSS + Resmî Gazete 11781) üzerinde
  soru, cevap, yasal dayanak ve madde/paragraf/span çıkarımı.
- İdempotency & Tekilleştirme: Aynı içerik tekrar tarandığında mükerrer kayıt üretilmemesi.
- Diff & Sürüm Yönetimi: İçerik değiştiğinde eski sürümün SUPERSEDED olması ve yeni sürüm oluşturulması.
- Moderasyon & Doğrulama: Bağımsız uzman onayı olmadan hiçbir kaydın verified=True yapılmaması,
  onay/ret süreçleri, audit log kaydı ve arama indeksine işleme.
- API Güvenliği: Yönetici anahtarı (admin key) koruması ve uç nokta denetimleri.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tarim_destek_rag.api.main import app
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.faq_repository import FAQRepository
from tarim_destek_rag.scraper.pipeline import (
    HarvestModerationService,
    OfficialFAQParser,
)
from tarim_destek_rag.scraper.source_registry import URLAllowlistRegistry

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def session():
    """İzole bellek SQLite oturumu."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sm = sessionmaker(bind=engine)
    sess = sm()
    yield sess
    sess.close()


# ==============================================================================
# 1. URL ALLOWLIST & SSRF KORUMASI TESTLERİ
# ==============================================================================


def test_url_allowlist_valid_domains():
    """Resmî alan adlarına ait geçerli HTTPS bağlantıları onaylanmalıdır."""
    valid_urls = [
        "https://www.tarimorman.gov.tr/BUGEM/Sayfalar/Detay.aspx?SayfaId=123",
        "https://tarimorman.gov.tr/Haber/7258",
        "https://resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf",
        "https://mevzuat.gov.tr/mevzuat?MevzuatNo=5488",
    ]
    for url in valid_urls:
        allowed, msg = URLAllowlistRegistry.validate_url(url)
        assert allowed is True, f"Geçerli URL reddedildi: {url} ({msg})"


def test_url_allowlist_blocks_non_https():
    """Güvenli olmayan HTTP protokolü reddedilmelidir."""
    allowed, msg = URLAllowlistRegistry.validate_url("http://www.tarimorman.gov.tr/duyurular")
    assert allowed is False
    assert "HTTPS" in msg


def test_url_allowlist_blocks_unauthorized_domains():
    """İzin listesinde olmayan dış alan adları engellenmelidir."""
    unauthorized_urls = [
        "https://example.com/tarim",
        "https://attacker.org/fake-support",
        "https://tarimorman.gov.tr.evil.com/index.html",
    ]
    for url in unauthorized_urls:
        allowed, msg = URLAllowlistRegistry.validate_url(url)
        assert allowed is False, f"Yetkisiz URL kabul edildi: {url}"


def test_url_allowlist_blocks_ssrf_attacks():
    """SSRF ve yerel IP erişim girişimleri kesinlikle engellenmelidir."""
    ssrf_urls = [
        "https://localhost/admin",
        "https://127.0.0.1:8000/secret",
        "https://192.168.1.100/router",
        "https://10.0.0.1/metadata",
        "https://169.254.169.254/latest/meta-data",
    ]
    for url in ssrf_urls:
        allowed, msg = URLAllowlistRegistry.validate_url(url)
        assert allowed is False, f"SSRF URL engellenemedi: {url}"
        assert "SSRF" in msg or "reddedildi" in msg


# ==============================================================================
# 2. EN AZ İKİ RESMÎ HTML FİXTURE ÜZERİNDE AYRIŞTIRMA VE ÇIKARIM TESTLERİ
# ==============================================================================


def test_parse_tarimorman_fixture():
    """Tarım Bakanlığı BÜGEM SSS HTML fixture'ı doğru ayrıştırılmalıdır."""
    fixture_path = FIXTURES_DIR / "tarimorman_faq_sample.html"
    assert fixture_path.exists(), f"Fixture bulunamadı: {fixture_path}"

    html_content = fixture_path.read_text(encoding="utf-8")
    items = OfficialFAQParser.parse_html(
        html_content,
        source_url="https://www.tarimorman.gov.tr/BUGEM/SSS",
        default_source_name="Tarım ve Orman Bakanlığı BÜGEM",
    )

    assert len(items) == 3
    # ÇKS sorusu
    assert any("ÇKS kaydı olan çiftçiler" in it["question"] for it in items)
    # Planlı üretim sorusu
    planned_item = next(it for it in items if "Planlı üretim" in it["question"])
    assert "954 TL/da" in planned_item["answer"]
    assert "11781 Sayılı" in planned_item["legal_citation"]
    assert "Madde 2" in planned_item["legal_span"]

    # Su kısıtı sorusu
    water_item = next(it for it in items if "su kısıtı" in it["question"])
    assert "250 TL/da" in water_item["answer"]
    assert "Madde 5" in water_item["legal_span"]


def test_parse_resmigazete_11781_fixture():
    """Resmî Gazete 11781 sayılı Karar metni fixture'ı tanım listesinden ayrıştırılmalıdır."""
    fixture_path = FIXTURES_DIR / "resmigazete_11781_sample.html"
    assert fixture_path.exists(), f"Fixture bulunamadı: {fixture_path}"

    html_content = fixture_path.read_text(encoding="utf-8")
    items = OfficialFAQParser.parse_html(
        html_content,
        source_url="https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf",
        default_source_name="T.C. Resmî Gazete (Karar 11781)",
    )

    assert len(items) == 2
    # Madde 1: 367 TL katsayı
    katsayi_item = next(it for it in items if "Destekleme Katsayısı" in it["question"])
    assert "367 TL/da" in katsayi_item["answer"]
    assert "Madde 1" in katsayi_item["legal_span"]

    # Madde 3: Tohum ve fidan desteği
    seed_item = next(it for it in items if "Sertifikalı Tohum" in it["question"])
    assert "120 TL/da" in seed_item["answer"]
    assert "400 TL/da" in seed_item["answer"]
    assert "Madde 3" in seed_item["legal_span"]


# ==============================================================================
# 3. İDEMPOTENCY, MÜKERRER KAYIT ENGELİ VE DİFF / SUPERSEDE TESTLERİ
# ==============================================================================


def test_harvest_moderation_idempotency(session):
    """Aynı resmî kaynak birden fazla tarandığında mükerrer kayıt üretilmemelidir."""
    fixture_path = FIXTURES_DIR / "tarimorman_faq_sample.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    service = HarvestModerationService(session)
    url = "https://www.tarimorman.gov.tr/BUGEM/SSS"

    # İlk tarama: 3 kayıt PENDING olarak oluşturulur
    r1 = service.harvest_from_source(url, override_html=html_content)
    assert r1["total_extracted"] == 3
    assert r1["new_pending"] == 3
    assert r1["skipped_duplicates"] == 0

    # İkinci tarama: Birebir aynı içerik -> 3 kayıt tekilleştirilir ve atlanır (skipped)
    r2 = service.harvest_from_source(url, override_html=html_content)
    assert r2["total_extracted"] == 3
    assert r2["new_pending"] == 0
    assert r2["skipped_duplicates"] == 3

    # Veritabanında sadece 3 kayıt olmalı
    repo = FAQRepository(session)
    assert len(repo.list_moderation_queue(status="PENDING")) == 3


def test_harvest_content_diff_supersedes_old_version(session):
    """Aynı soru için mevzuat/cevap güncellendiğinde eski kayıt SUPERSEDED olmalı, yeni versiyon PENDING açılmalıdır."""
    service = HarvestModerationService(session)
    repo = FAQRepository(session)
    url = "https://www.tarimorman.gov.tr/BUGEM/SSS"

    initial_html = """
    <article class="faq-item">
        <h3 class="question">2026 yılı buğday desteği ne kadardır?</h3>
        <div class="answer">
            <p>Eski karar: Buğday desteği 850 TL olarak belirlenmiştir.</p>
            <p class="citation">Resmî Karar Eski Sayı</p>
        </div>
    </article>
    """
    # 1. İlk tarama
    r1 = service.harvest_from_source(url, override_html=initial_html)
    assert r1["new_pending"] == 1

    # İlk kaydı moderatör onaylasın
    pending = repo.list_moderation_queue(status="PENDING")[0]
    service.approve_item(pending.id, admin_user="tarim_uzmani")
    approved_v1 = repo.get_by_id(pending.id)
    assert approved_v1.moderation_status == "APPROVED"
    assert approved_v1.verified is True
    assert approved_v1.version == 1

    # 2. Mevzuat değişikliği yayınlandı: Tutar 954 TL olarak güncellendi
    updated_html = """
    <article class="faq-item">
        <h3 class="question">2026 yılı buğday desteği ne kadardır?</h3>
        <div class="answer">
            <p>Yeni karar 11781: Buğday desteği 954 TL olarak güncellenmiştir.</p>
            <p class="citation">Resmî Gazete Karar No: 11781</p>
        </div>
    </article>
    """
    r2 = service.harvest_from_source(url, override_html=updated_html)
    assert r2["new_pending"] == 1
    assert r2["superseded_count"] == 1

    # Eski kayıt SUPERSEDED ve unverified olmalı
    old_item = repo.get_by_id(pending.id)
    assert old_item.moderation_status == "SUPERSEDED"
    assert old_item.verified is False

    # Yeni kayıt v2 ve PENDING olmalı
    pending_list = repo.list_moderation_queue(status="PENDING")
    assert len(pending_list) == 1
    new_item = pending_list[0]
    assert new_item.version == 2
    assert "954 TL" in new_item.answer
    assert new_item.verified is False  # Henüz onaylanmadı!


# ==============================================================================
# 4. MODERASYON, ONAY/RET VE AUDIT LOG TESTLERİ
# ==============================================================================


def test_unverified_records_not_presented_as_verified(session):
    """Canlı taranan kayıtlar bağımsız moderatör onayı olmadan ASLA verified sunulamaz."""
    service = HarvestModerationService(session)
    repo = FAQRepository(session)
    url = "https://www.tarimorman.gov.tr/BUGEM/SSS"

    html = """
    <article class="faq-item">
        <h3 class="question">Doğrulanmamış test sorusu?</h3>
        <div class="answer"><p>Cevap içeriği buradadır.</p></div>
    </article>
    """
    service.harvest_from_source(url, override_html=html)
    items = repo.list_moderation_queue(status="PENDING")
    assert len(items) == 1
    item = items[0]

    assert item.verified is False
    assert item.moderation_status == "PENDING"

    # Çiftçi aramasında sadece onaylılar görünsün
    verified_faqs = repo.list_faqs(only_verified=True)
    assert not any(f.id == item.id for f in verified_faqs)

    # Moderatör onayı
    service.approve_item(item.id, admin_user="tarim_uzmani")
    approved_item = repo.get_by_id(item.id)
    assert approved_item.verified is True
    assert approved_item.moderation_status == "APPROVED"

    # Şimdi doğrulanmış listesinde görünmeli
    assert any(f.id == item.id for f in repo.list_faqs(only_verified=True))


def test_moderation_reject_flow(session):
    """Moderatör hatalı veya gereksiz kaydı gerekçeli reddedebilmelidir."""
    service = HarvestModerationService(session)
    repo = FAQRepository(session)
    url = "https://www.tarimorman.gov.tr/BUGEM/SSS"

    html = """
    <article class="faq-item">
        <h3 class="question">Hatalı veya eksik mevzuat sorusu?</h3>
        <div class="answer"><p>Yetersiz cevap.</p></div>
    </article>
    """
    service.harvest_from_source(url, override_html=html)
    item = repo.list_moderation_queue(status="PENDING")[0]

    rejected = service.reject_item(item.id, reason="Mevzuat dayanağı eksik ve tutarsız", admin_user="denetmen")
    assert rejected.moderation_status == "REJECTED"
    assert rejected.verified is False

    # Denetim günlüğünde işlem kaydedilmiş olmalı
    logs = repo.get_audit_logs()
    assert any(entry.action == "REJECT" and entry.faq_id == item.id for entry in logs)


# ==============================================================================
# 5. FASTAPI GÜVENLİK VE UÇ NOKTA ENTEGRASYON TESTLERİ
# ==============================================================================


def test_api_harvest_live_security(monkeypatch):
    """Canlı tarama uç noktası yönetici anahtarı ve izinli alan adı kurallarına uymalıdır."""
    with TestClient(app) as client:
        # 1. Admin anahtarı yoksa 503
        monkeypatch.delenv("TARIM_RAG_ADMIN_API_KEY", raising=False)
        payload = {"source_url": "https://www.tarimorman.gov.tr/BUGEM/SSS"}
        assert client.post("/faqs/harvest-live", json=payload).status_code == 503

        # 2. Yanlış admin anahtarı ile 403
        monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", "super-secret-key")
        assert client.post(
            "/faqs/harvest-live",
            json=payload,
            headers={"X-Admin-Key": "wrong-key"},
        ).status_code == 403

        # 3. İzin verilmeyen alan adı tarama talebi 400 döner
        bad_payload = {"source_url": "https://unauthorized-domain.com/faqs"}
        resp_bad = client.post(
            "/faqs/harvest-live",
            json=bad_payload,
            headers={"X-Admin-Key": "super-secret-key"},
        )
        assert resp_bad.status_code == 400
        err_msg = resp_bad.json().get("message") or resp_bad.json().get("detail", "")
        assert "Erişim reddedildi" in err_msg


def test_api_moderation_queue_and_actions(monkeypatch):
    """Moderasyon listeleme, onaylama ve denetim kütüğü uç noktaları çalışmalıdır."""
    with TestClient(app) as client:
        monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", "super-secret-key")
        headers = {"X-Admin-Key": "super-secret-key"}

        # Moderasyon kuyruğu listeleme
        resp_queue = client.get("/faqs/moderation-queue", headers=headers)
        assert resp_queue.status_code == 200
        assert isinstance(resp_queue.json(), list)

        # Denetim logları listeleme
        resp_logs = client.get("/faqs/moderation-logs", headers=headers)
        assert resp_logs.status_code == 200
        assert isinstance(resp_logs.json(), list)
