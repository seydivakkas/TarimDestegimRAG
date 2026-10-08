"""TarımDestekRAG PC Gradio Arayüzü.

Türkiye 2026 Bitkisel Üretim Destekleri Deterministik Karar ve Açıklama Asistanı.
Master Plan doğrultusunda 9 sekmeli zengin kullanıcı arayüzü sunar:
1. Profil & Parsel Girişi (Çiftçi ve Parsel Bilgileri + Canlı Hak Ediş Özeti)
2. Desteklerim (Uygunluk Rozetleri ve Tahmini Tutar Kartları)
3. Destek Detay (Hesaplama Tablosu, Başvuru Takvimi ve Gerekli Belgeler)
4. Neden? (Gerekçe, Eksik Belgeler ve Resmî Gazete Atıfları)
5. Soru-Cevap Asistanı (Sıfır LLM Semantik Mevzuat Arama)
6. Mevzuat & Kazıyıcı Paneli (Takip Edilen Resmî Kaynaklar ve Sürümleme)
7. Doğrulama & Benchmark (100 Resmî Test Vakası)
8. Admin Paneli & Sistem Mimarisi (Zero-LLM ve Lisans Bildirimi)
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import gradio as gr
import pandas as pd

# Proje kök dizinini ve backend/src dizinini sys.path'e ekle
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_BACKEND_SRC = _ROOT / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

try:
    from frontend_pc.api_client import ApiClient
    from frontend_pc.geo_data import TURKEY_DISTRICTS, TURKEY_PROVINCES
    from frontend_pc.theme import CUSTOM_CSS, get_tarim_theme
except ModuleNotFoundError:
    from api_client import ApiClient  # type: ignore[no-redef]
    from geo_data import TURKEY_DISTRICTS, TURKEY_PROVINCES  # type: ignore[no-redef]
    from theme import CUSTOM_CSS, get_tarim_theme  # type: ignore[no-redef]

from tarim_destek_rag.citations.document_links import (  # noqa: E402
    format_citation_section_header,
    format_clickable_action,
    format_clickable_check,
    format_highlighted_citation_card,
    render_document_viewer_html,
    resolve_check_link,
)

# API İstemcisi
api_client = ApiClient()

# Türkiye 81 İl ve Tüm İlçeler
PROVINCES = TURKEY_PROVINCES
DISTRICTS = TURKEY_DISTRICTS

CROPS = [
    "BUĞDAY", "ARPA", "MISIR", "AYÇİÇEĞİ", "PAMUK", "FINDIK",
    "MERCİMEK", "NOHUT", "SOYA", "ÇELTİK", "KANOLA", "ASPİR",
    "KURU FASULYE", "PATATES", "ZEYTİN", "YEM BİTKİLERİ"
]


def parse_tri_state(val: str | bool | None) -> bool | None:
    """Evet / Hayır / Bilmiyorum veya boolean değerleri normalize eder.

    'Bilmiyorum / Emin Değilim' seçildiğinde veya None olduğunda None döner.
    Bu durum kural motorunun REVIEW (Eksik Bilgi / İnceleme) mekanizmasını tetikler.
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if "bilmiyorum" in s or "emin değilim" in s or "belirsiz" in s or "?" in s:
        return None
    if "evet" in s or "aktif" in s or "var" in s or "kapama" in s or "✅" in s:
        return True
    if "hayır" in s or "yok" in s or "pasif" in s or "münferit" in s or "❌" in s:
        return False
    return None


def parse_irrigation_status(value: str | None) -> str:
    """UI sulama seçimini API Parcel.irrigation enum değerine dönüştürür."""
    text = str(value or "").strip().lower()
    if "bilmiyorum" in text or "emin değilim" in text or "?" in text:
        return "UNKNOWN"
    if "kuru" in text:
        return "DRY"
    if "sulu" in text:
        return "IRRIGATED"
    return "UNKNOWN"


def load_benchmark_data() -> pd.DataFrame:
    """Benchmark veri setini okur ve 100 vakalık detaylı özet tablo oluşturur."""
    bench_file = Path("benchmark/cases.jsonl")
    if not bench_file.exists():
        bench_file = Path("data/benchmark/cases.jsonl")
    if not bench_file.exists():
        return pd.DataFrame()

    # Vaka tanımları test sonucu değildir. Önce kaydedilmiş koşu sonuçlarını eşleştir.
    run_results = {}
    results_file = Path("benchmark/results.csv")
    if results_file.exists():
        for result in pd.read_csv(results_file).to_dict("records"):
            run_results[str(result.get("case_id", ""))] = result

    records = []
    with open(bench_file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            province = item.get("province") or item.get("farmer", {}).get("province", "-")
            district = item.get("district") or item.get("farmer", {}).get("district", "-")
            crop = item.get("crop") or item.get("parcel", {}).get("crop", "-")
            area_da = item.get("area_da") or item.get("parcel", {}).get("area_da", "-")
            expected_amt = item.get("expected_amount")
            amt_str = (
                f"{float(expected_amt):,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
                if expected_amt
                else "-"
            )

            result = run_results.get(str(item.get("case_id")), {})
            if not result:
                test_label = "Ölçülmedi"
            elif str(result.get("status_match", "")).lower() == "true" and str(
                result.get("amount_match", "")
            ).lower() == "true":
                test_label = "Kaydedilmiş: başarılı"
            else:
                test_label = "Kaydedilmiş: başarısız"

            records.append(
                {
                    "Vaka ID": item.get("case_id"),
                    "Kategori": item.get("category", "-"),
                    "İl / İlçe": f"{province}/{district}",
                    "Ürün": crop,
                    "Alan (da)": f"{float(area_da):.1f}" if str(area_da).replace(".", "").isdigit() else str(area_da),
                    "Hedef Destek": item.get("support_id", "-"),
                    "Beklenen Karar": item.get("expected_status", "-"),
                    "Beklenen Tutar": amt_str,
                    "Test Doğrulaması": test_label,
                }
            )
    return pd.DataFrame(records)


def get_benchmark_summary() -> str:
    """Son kaydedilmiş vaka eşleşmelerini gösterir; güncellik/metinsel atıf kanıtı değildir."""
    data = load_benchmark_data()
    if data.empty:
        return "Henüz benchmark vaka verisi bulunmuyor."
    labels = data["Test Doğrulaması"]
    measured = int(labels.str.startswith("Kaydedilmiş:").sum())
    passed = int((labels == "Kaydedilmiş: başarılı").sum())
    return (
        f"**{len(data)} tanımlı vaka · {measured} kaydedilmiş vaka sonucu · "
        f"{passed} kaydedilmiş başarılı eşleşme.** "
        "Kaynak: `benchmark/results.csv`. Bu sayılar güncel mevzuat geçerliliğini, "
        "bağımsız atıf denetimini veya gerçek zamanlı benchmark çalışmasını kanıtlamaz."
    )


def format_currency(val: float | int | str | None) -> str:
    """Türk Lirası para birimi biçimlendirici."""
    if val is None:
        return "Hesaplanmadı"
    try:
        f_val = float(val)
        return f"{f_val:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "Doğrulama gerekli"


def evaluate_farmer_parcel(
    province: str,
    district: str,
    cks_status: str | bool | None,
    age_group: str,
    gender: str,
    crop: str,
    area_da: float,
    irrigation_type: str,
    seed_cert: str | bool | None,
    sapling_cert: str | bool | None,
    closed_orchard: str | bool | None,
    client: ApiClient | None = None,
) -> tuple[str, str, pd.DataFrame, str, str, str]:
    """Çiftçi ve parsel verisini FastAPI arka ucuna gönderir ve sonuçları biçimlendirir."""
    active_client = client or api_client
    parsed_cks = parse_tri_state(cks_status)
    parsed_seed = parse_tri_state(seed_cert)
    parsed_sapling = parse_tri_state(sapling_cert)
    parsed_orchard = parse_tri_state(closed_orchard)

    farmer_data = {
        "farmer_id": "FARMER-DEMO-001",
        "province": province.strip().upper(),
        "district": district.strip().upper(),
        "cks_status": parsed_cks,
        "age_group": "<41" if "Genç" in age_group else "STANDARD",
        "gender": "KADIN" if "Kadın" in gender else "ERKEK",
    }

    parcel_data = {
        "parcel_id": "PARCEL-DEMO-001",
        "farmer_id": "FARMER-DEMO-001",
        "crop": crop.strip().upper(),
        "area_da": float(area_da),
        "production_year": 2026,
        "irrigation": parse_irrigation_status(irrigation_type),
        "seed_certificate_available": parsed_seed,
        "sapling_certificate_available": parsed_sapling,
        "is_closed_orchard": parsed_orchard,
    }

    resp = active_client.evaluate_full(farmer_data, parcel_data)
    if "error" in resp:
        err_msg = f"<div class='disclaimer-box'>⚠️ <b>Hata:</b> {resp['error']}</div>"
        return err_msg, "", pd.DataFrame(), "", "", err_msg

    rules = resp.get("rules", [])
    calculations = resp.get("calculations", [])
    explanations_list = resp.get("explanations", [])
    total_payout = resp.get("total_estimated_amount", 0.0)

    # Sözlük eşlemeleri
    exp_map = {e.get("support_id"): e for e in explanations_list}
    calc_map = {c.get("support_id"): c for c in calculations}

    # Hesaplayıcı, birim tutar bulunamadığında kuraldan daha temkinli REVIEW dönebilir.
    effective_statuses = [
        calc_map.get(r.get("support_id"), {}).get("status", r.get("status"))
        for r in rules
    ]
    eligible_count = effective_statuses.count("ELIGIBLE")
    review_count = effective_statuses.count("REVIEW")
    ineligible_count = effective_statuses.count("NOT_ELIGIBLE")

    # 1. Tab 1 Canlı Özet Kartı (Inline Summary)
    inline_chips = ""
    for r in rules:
        sid = r.get("support_id")
        sname = r.get("support_name", sid)
        c = calc_map.get(sid, {})
        st = c.get("status", r.get("status"))
        amt = c.get("estimated_amount")

        if st == "ELIGIBLE":
            badge = "<span class='badge-eligible'>UYGUN</span>"
            item_class = "eligible"
        elif st == "REVIEW":
            badge = "<span class='badge-review'>İNCELEME</span>"
            item_class = "review"
        else:
            badge = "<span class='badge-ineligible'>UYGUN DEĞİL</span>"
            item_class = "ineligible"

        inline_chips += f"""
        <div class="inline-support-item {item_class}">
            <div>
                <b style="color: #1e293b; font-size: 0.95rem;">{sname}</b><br/>
                <span style="font-size: 0.85rem; color: #64748b;">Hak Ediş: <b>{format_currency(amt)}</b></span>
            </div>
            <div>{badge}</div>
        </div>
        """

    inline_html = f"""
    <div class="inline-summary-box">
        <div class="inline-summary-header">
            <div>
                <h3 style="margin: 0; color: #166534; font-size: 1.35rem;">2026 Tarımsal Destek Ön Değerlendirmesi</h3>
                <p style="margin: 4px 0 0 0; color: #15803d; font-size: 0.95rem;">
                    Parsel: <b>{float(area_da):.1f} da {crop.upper()}</b> &middot; Konum: <b>{province.upper()} / {district.upper()}</b>
                </p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.85rem; color: #166534; font-weight: 700; text-transform: uppercase;">Hesaplanabilen Destekler Toplamı</div>
                <div class="inline-summary-payout">{format_currency(total_payout)}</div>
            </div>
        </div>
        <div style="display: flex; gap: 12px; margin-bottom: 8px;">
            <span class="badge-eligible">✅ {eligible_count} Uygun</span>
            <span class="badge-review">⚠️ {review_count} İnceleme / Eksik Belge</span>
            <span class="badge-ineligible">❌ {ineligible_count} Uygun Değil</span>
        </div>
        <div class="inline-chips-grid">
            {inline_chips}
        </div>
        <div style="margin-top: 16px; padding: 10px 14px; background: #e0f2fe; border-radius: 8px; color: #0369a1; font-size: 0.9rem;">
            💡 <b>Sonraki Adım:</b> Detaylı hesaplama formülleri ve başvuru takvimi için <b>"📋 Desteklerim"</b> ve <b>"🔍 Destek Detay"</b> sekmelerine; Resmî Gazete madde alıntıları için <b>"📜 Neden?"</b> sekmesine geçebilirsiniz.
        </div>
    </div>
    """

    # 2. Tab 2 KPI Kartları HTML
    kpi_html = f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-title">Hesaplanabilen Tahmini Toplam</div>
            <div class="kpi-value green">{format_currency(total_payout)}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Uygun Destekler</div>
            <div class="kpi-value green">{eligible_count} / {len(rules)}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">İnceleme / Ek Belge</div>
            <div class="kpi-value gold">{review_count}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Uygun Değil</div>
            <div class="kpi-value" style="color: #991b1b;">{ineligible_count}</div>
        </div>
    </div>
    """

    # 3. Tab 2 Desteklerim Kart Listesi HTML
    cards_html = "<div style='display: flex; flex-direction: column; gap: 14px; margin-top: 10px;'>"
    table_rows = []

    for ev in rules:
        sid = ev.get("support_id")
        sname = ev.get("support_name", sid)
        calc = calc_map.get(sid, {})
        status = calc.get("status", ev.get("status"))
        total_amt = calc.get("estimated_amount")
        unit_amt = calc.get("unit_amount")
        formula = calc.get("formula", "-")

        exp = exp_map.get(sid, {})
        summary_tr = exp.get("summary_tr") or "Değerlendirme tamamlandı."
        detailed_reason = exp.get("detailed_reason_tr", "")

        if status == "ELIGIBLE":
            badge_class = "badge-eligible"
            card_class = "eligible"
            status_text = "ÖN DEĞERLENDİRME: UYGUN"
        elif status == "REVIEW":
            badge_class = "badge-review"
            card_class = "review"
            status_text = "İNCELEME / EKSİK BELGE"
        else:
            badge_class = "badge-ineligible"
            card_class = "ineligible"
            status_text = "UYGUN DEĞİL"

        cards_html += f"""
        <div class="support-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h3 style="margin: 0; font-size: 1.15rem; color: #1e293b;">{sname}</h3>
                <span class="{badge_class}">{status_text}</span>
            </div>
            <div style="margin: 8px 0; color: #334155; font-size: 0.95rem; line-height: 1.5;">
                <b>Özet:</b> {summary_tr}
                {f'<br/><span style="color: #64748b; font-size: 0.9rem;">{detailed_reason}</span>' if detailed_reason else ''}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 12px; border-top: 1px dashed #e2e8f0; padding-top: 8px;">
                <span style="font-size: 0.88rem; color: #64748b;">Formül: <code>{formula}</code></span>
                <div style="font-size: 1.35rem; font-weight: 800; color: #0f172a; white-space: nowrap;">
                    {format_currency(total_amt)}
                </div>
            </div>
        </div>
        """

        table_rows.append(
            {
                "Destek Programı": sname,
                "Durum": status_text,
                "Birim Fiyat (TL/da)": f"{float(unit_amt):.2f} ₺" if unit_amt is not None and float(unit_amt) > 0 else "Doğrulama gerekli",
                "Alan (da)": f"{area_da:.1f}",
                "Tahmini Tutar": format_currency(total_amt),
                "Hesaplama Formülü": formula,
                "Başvuru Dönemi": "Program bazında kaynak doğrulaması gerekli",
                "Dayanak": "Kaynak/sürüm kontrolü gerekli",
            }
        )

    cards_html += "</div>"
    details_df = pd.DataFrame(table_rows)

    # 4. Tab 4 Neden? (Gerekçe, Eksikler ve Resmî Gazete Atıfları)
    reasons_markdown = "### 📜 Kural Motoru İşletim Gerekçeleri ve Resmî Mevzuat Dayanakları\n\n"
    for ev in rules:
        sid = ev.get("support_id")
        sname = ev.get("support_name", sid)
        status = ev.get("status")
        passed = ev.get("passed_checks", [])
        failed = ev.get("failed_checks", [])
        mfields = ev.get("missing_fields", [])
        trace = ev.get("trace", "")

        exp = exp_map.get(sid, {})
        summary_tr = exp.get("summary_tr", "-")
        detailed_reason = exp.get("detailed_reason_tr", "")
        next_actions = exp.get("next_actions_tr", [])
        citations = exp.get("citations", [])

        status_emoji = "✅" if status == "ELIGIBLE" else ("⚠️" if status == "REVIEW" else "❌")
        reasons_markdown += f"#### {status_emoji} {sname}\n\n"
        reasons_markdown += f"- **Kural Durum Kodları:** `{status}` &middot; `{trace}`\n"
        reasons_markdown += f"- **Açıklama:** {summary_tr}\n"
        if detailed_reason:
            reasons_markdown += f"- **Detaylı Gerekçe:** {detailed_reason}\n"

        if passed:
            reasons_markdown += "\n**Sağlanan Şartlar:**\n\n"
            for p in passed:
                reasons_markdown += f"{format_clickable_check(p, '✅', sid)}\n\n"

        if failed:
            reasons_markdown += "\n**Sağlanamayan Şartlar (Ret Gerekçeleri):**\n\n"
            for f_item in failed:
                reasons_markdown += f"{format_clickable_check(f_item, '❌', sid)}\n\n"

        if mfields:
            reasons_markdown += "\n**Eksik Alanlar / Belgeler (Ne Eksik?):**\n\n"
            for m in mfields:
                m_text = f"{m} belgesi/bilgisi tamamlandığında yeniden değerlendirilir."
                reasons_markdown += f"{format_clickable_check(m_text, '⚠️', sid)}\n\n"

        if next_actions:
            reasons_markdown += "\n**Yapılması Gereken Başvuru Adımları:**\n\n"
            for act in next_actions:
                reasons_markdown += f"{format_clickable_action(act, sid)}\n\n"

        if citations:
            first_cit_url = citations[0].get("url") if isinstance(citations[0], dict) else None
            reasons_markdown += f"\n- {format_citation_section_header(first_cit_url)}:\n\n"
            for cit in citations:
                reasons_markdown += f"{format_highlighted_citation_card(cit, status, sid)}\n\n"

        reasons_markdown += "\n---\n\n"

    # 5. Yasal Uyarı
    disclaimer_html = """
    <div class='disclaimer-box'>
        ⚖️ <b>Yasal Uyarı ve Sorumluluk Reddi:</b> Bu sistemde üretilen uygunluk durumları ve parasal tutarlar,
        Resmî Gazete'de yayımlanan 2026 bitkisel üretim destekleme mevzuatına dayalı <b>tahmini bir ön değerlendirmedir</b>.
        Kesin hak sahipliği, icmal listeleri ve ödemeler Tarım ve Orman Bakanlığı İl/İlçe Müdürlüklerinin yetkisindedir.
    </div>
    """

    return kpi_html, cards_html, details_df, reasons_markdown, disclaimer_html, inline_html


def generate_evaluation_report(
    province: str,
    district: str,
    cks_status: str | bool | None,
    age_group: str,
    gender: str,
    crop: str,
    area_da: float,
    irrigation_type: str,
    seed_cert: str | bool | None,
    sapling_cert: str | bool | None,
    closed_orchard: str | bool | None,
    client: ApiClient | None = None,
) -> dict:
    """Bağımsız yazılımın resmî olmayan ön değerlendirme raporunu hazırlar."""
    active_client = client or api_client
    parsed_cks = parse_tri_state(cks_status)
    parsed_seed = parse_tri_state(seed_cert)
    parsed_sapling = parse_tri_state(sapling_cert)
    parsed_orchard = parse_tri_state(closed_orchard)

    farmer_data = {
        "farmer_id": "FARMER-REPORT-001",
        "province": province.strip().upper(),
        "district": district.strip().upper(),
        "cks_status": parsed_cks,
        "age_group": "<41" if "Genç" in age_group else "STANDARD",
        "gender": "KADIN" if "Kadın" in gender else "ERKEK",
    }
    parcel_data = {
        "parcel_id": "PARCEL-REPORT-001",
        "farmer_id": "FARMER-REPORT-001",
        "crop": crop.strip().upper(),
        "area_da": float(area_da),
        "production_year": 2026,
        "irrigation": parse_irrigation_status(irrigation_type),
        "seed_certificate_available": parsed_seed,
        "sapling_certificate_available": parsed_sapling,
        "is_closed_orchard": parsed_orchard,
    }

    resp = active_client.evaluate_full(farmer_data, parcel_data)
    if "error" in resp:
        return gr.update(value=None, visible=False)

    total_payout = resp.get("total_estimated_amount", 0.0)
    rules = resp.get("rules", [])
    calculations = resp.get("calculations", [])
    explanations = resp.get("explanations", [])
    calc_map = {c.get("support_id"): c for c in calculations}
    exp_map = {e.get("support_id"): e for e in explanations}

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    cks_txt = (
        "✅ Aktif / Kayıtlı"
        if parsed_cks is True
        else ("❌ Kayıt Bulunamadı" if parsed_cks is False else "❓ Bilinmiyor / Beyan Edilmedi (Ek İnceleme Gerekli)")
    )
    seed_txt = (
        "✅ Mevcut / Faturalı"
        if parsed_seed is True
        else ("❌ Sertifikasız / Yok" if parsed_seed is False else "❓ Bilinmiyor / Beyan Edilmedi")
    )
    sapling_txt = (
        "✅ Mevcut / Faturalı"
        if parsed_sapling is True
        else ("❌ Standart / Yok" if parsed_sapling is False else "❓ Bilinmiyor / Beyan Edilmedi")
    )
    orchard_txt = (
        "Evet (Kapama Bahçe)"
        if parsed_orchard is True
        else ("Hayır" if parsed_orchard is False else "❓ Bilinmiyor / Beyan Edilmedi")
    )

    report_lines = [
        "# TarımDestekRAG — Bağımsız Yazılım Raporu",
        "## 2026 Bitkisel Üretim Destekleri — Tahmini Ön Değerlendirme",
        "",
        "**Bu belge Tarım ve Orman Bakanlığı tarafından düzenlenmiş veya onaylanmış resmî bir belge değildir.**",
        "",
        f"**Rapor Tarihi:** {now_str}",
        "**Doğrulama Motoru:** TarımDestekRAG Deterministik Kural Motoru (Zero-LLM)",
        "**Yasal Dayanak:** 2026 Resmî Gazete Bitkisel Üretim Kararları & BÜGEM Havza Tebliğleri",
        "",
        "---",
        "### 👤 1. Üretici ve Parsel Kayıt Özeti",
        f"- **Üretim Yeri:** {province.upper()} / {district.upper()}",
        f"- **Çiftçi Kayıt Sistemi (ÇKS):** {cks_txt}",
        f"- **Üretici Profili:** {gender} ({age_group})",
        f"- **Parsel Alanı:** {float(area_da):.1f} Dekar (da)",
        f"- **Ürün:** {crop.upper()}",
        f"- **Sulama Türü:** {irrigation_type}",
        f"- **Sertifikalı Tohum Faturası:** {seed_txt}",
        f"- **Sertifikalı Fidan Faturası:** {sapling_txt}",
        f"- **Kapama Meyve Bahçesi:** {orchard_txt}",
        "",
        "---",
        "### 💰 2. Hak Ediş Hesaplama Tablosu",
        "",
        f"#### 🎯 TOPLAM TAHMİNİ HAK EDİŞ: **{format_currency(total_payout)}**",
        "",
        "| Destek Kalemi | Uygunluk Durumu | Birim Fiyat | Alan (da) | Tahmini Tutar | Yasal Dayanak |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in rules:
        sid = r.get("support_id")
        sname = r.get("support_name", sid)
        st = r.get("status", "NOT_ELIGIBLE")
        c = calc_map.get(sid, {})
        amt = c.get("estimated_amount", 0.0)
        uamt = c.get("unit_amount", 0.0)
        st_tr = "✅ UYGUN" if st == "ELIGIBLE" else ("⚠️ İNCELEME" if st == "REVIEW" else "❌ UYGUN DEĞİL")
        report_lines.append(
            f"| {sname} | {st_tr} | {format_currency(uamt)}/da | {float(area_da):.1f} da | {format_currency(amt)} | 2026 Resmî Gazete |"
        )

    report_lines.extend([
        "",
        "---",
        "### 📜 3. Kural Değerlendirme Gerekçeleri ve Yasal Atıflar",
        "",
    ])

    for r in rules:
        sid = r.get("support_id")
        sname = r.get("support_name", sid)
        exp = exp_map.get(sid, {})
        reason = exp.get("detailed_reason_tr") or exp.get("summary_tr", "Kural değerlendirmesi tamamlandı.")
        report_lines.append(f"#### 📌 {sname}")
        report_lines.append(f"- **Gerekçe:** {reason}")
        if exp.get("passed_checks"):
            p_items = [
                f"[{p} ↗]({resolve_check_link(p, sid)['url']})"
                for p in exp.get("passed_checks")
            ]
            report_lines.append(f"- **Sağlanan Şartlar:** {' · '.join(p_items)}")
        if exp.get("failed_checks"):
            f_items = [
                f"[{f} ↗]({resolve_check_link(f, sid)['url']})"
                for f in exp.get("failed_checks")
            ]
            report_lines.append(f"- **Sağlanamayan Şartlar:** {' · '.join(f_items)}")
        if exp.get("missing_fields"):
            m_items = [
                f"[{m} ↗]({resolve_check_link(m, sid)['url']})"
                for m in exp.get("missing_fields")
            ]
            report_lines.append(f"- **Eksik Bilgi/Belgeler:** {', '.join(m_items)}")
        if exp.get("citations"):
            for cit in exp.get("citations", []):
                cit_url = cit.get("url") or resolve_check_link(cit.get("section", ""), sid)["url"]
                report_lines.append(f"- **Yasal Dayanak:** [{cit.get('title')} ({cit.get('section', '')}) ↗]({cit_url})")
        report_lines.append("")

    report_lines.extend([
        "---",
        "### ⚖️ 4. Yasal Uyarı ve Sorumluluk Reddi",
        "Bu rapor, Tarım ve Orman Bakanlığı tarafından Resmî Gazete'de yayımlanan 2026 yılı bitkisel üretim",
        "destekleme mevzuatına dayalı bir **tahmini ön değerlendirme çıktısıdır**.",
        "Kesin hak sahipliği, askı icmalleri ve ödeme takvimi İl/İlçe Tarım ve Orman Müdürlüklerinin yetkisindedir.",
        "",
        "---",
        f"*Rapor No: TDRAG-2026-{int(time.time())} | Lisans: Özel Lisans (c) 2026 Seydi Eryılmaz (@seydivakkas)*",
    ])

    out_dir = Path("data") / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / f"tarim_destek_on_degerlendirme_raporu_{int(time.time())}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    return gr.update(value=str(report_file.resolve()), visible=True)


def ask_assistant(
    user_message: str, chat_history: list[dict[str, str]]
) -> tuple[str, list[dict[str, str]]]:
    """Chatbot / Semantik Arama Asistanı (Sıfır LLM - Doğrulanmış Mevzuat)."""
    if not user_message or not user_message.strip():
        return "", chat_history

    resp = api_client.ask(user_message.strip(), top_k=3)
    answer = (
        resp.get("summary_answer_tr")
        or resp.get("answer")
        or "Sorunuza ilişkin mevzuatta doğrudan eşleşen madde bulunamadı."
    )
    chunks = resp.get("matched_chunks") or resp.get("citations", [])

    formatted_reply = f"{answer}\n\n"
    if chunks:
        formatted_reply += "---\n#### 🏛️ Doğrulanmış Resmî Mevzuat Dayanakları & Alıntılar (İşaretli Kanıt Metni):\n"
        for i, c in enumerate(chunks[:3], 1):
            if isinstance(c, dict):
                src = c.get("source_id", "RG")
                title = c.get("title", "Resmî Gazete")
                sec = c.get("section") or c.get("article_ref", "") or "Madde"
                raw_t = c.get("text", "")
                url = c.get("url")
                cit_dict = {
                    "title": f"[{i}] {title}",
                    "section": f"{sec} ({src})",
                    "year": 2026,
                    "snippet": raw_t if len(raw_t) <= 260 else raw_t[:260] + "...",
                    "url": url,
                }
                formatted_reply += f"{format_highlighted_citation_card(cit_dict, 'ELIGIBLE')}\n\n"
            else:
                formatted_reply += f'\n> **[{i}]** *"{c}"*\n'

    new_history = list(chat_history)
    new_history.append({"role": "user", "content": user_message})
    new_history.append({"role": "assistant", "content": formatted_reply})

    return "", new_history


def get_sources_table() -> pd.DataFrame:
    """Kayıtlı mevzuat kaynakları listesini getirir."""
    sources = api_client.get_sources()
    rows = []
    for s in sources:
        rows.append(
            {
                "Kaynak Kodu": s.get("id") or s.get("source_id"),
                "Otorite": s.get("authority"),
                "Başlık": s.get("title"),
                "Format": s.get("content_type"),
                "Öncelik": s.get("priority", 0),
                "URL / Erişim": s.get("url"),
            }
        )
    return pd.DataFrame(rows)


def get_application_windows_table() -> pd.DataFrame:
    """2026 Destekleme Programları ve Başvuru Takvimini dinamik getirir."""
    supports = api_client.get_supports()
    rows = []
    for s in supports:
        rows.append(
            {
                "Destek Programı": s.get("name", s.get("id")),
                "Başlangıç Tarihi": s.get("application_start") or "Kaynak doğrulaması gerekli",
                "Bitiş Tarihi": s.get("application_end") or "Kaynak doğrulaması gerekli",
                "Durum": "Takvim ayrıca teyit edilmeli" if s.get("active", True) else "Program pasif",
                "Açıklama": s.get("description", "-"),
            }
        )
    return pd.DataFrame(rows)


def get_faq_categories() -> list[str]:
    """Tüm benzersiz SSS kategorilerini listeler."""
    faqs = api_client.get_faqs()
    cats = sorted(list({f.get("category", "") for f in faqs if f.get("category")}))
    return ["Tümü"] + cats


def get_faq_banner_text() -> str:
    """SSS veritabanı istatistik özet metnini döner."""
    stats = api_client.get_faq_stats()
    total = stats.get("total_count", 0)
    verified = stats.get("verified_count", 0)
    cats = len(stats.get("category_counts", {}))
    if total > 0:
        return (
            f"📚 **Doğrulanmış Tarımsal Çözüm Veritabanı:** Toplam **{total} adet** kayıt "
            f"({verified} doğrulanmış olarak işaretli, {cats} kategori). Bu kayıtların mevzuatla güncelliği ayrıca kontrol edilmelidir. "
            "Aşağıdaki tablodan soru seçebilir veya yukarıdaki sohbet alanına serbestçe yazabilirsiniz."
        )
    return (
        "📚 **Doğrulanmış Tarımsal Çözüm Veritabanı:** Yürürlükteki mevzuat ve ziraî rehberler indekslenmiştir."
    )


def get_faq_table(category_filter: str = "Tümü", search_query: str = "") -> pd.DataFrame:
    """Kategori ve arama kriterine göre filtrelenmiş SSS tablosu döner."""
    cat_param = None if category_filter == "Tümü" else category_filter
    faqs = api_client.get_faqs(category=cat_param, search=search_query)
    rows = []
    for f in faqs:
        ans_short = f.get("answer", "")
        if len(ans_short) > 130:
            ans_short = ans_short[:127] + "..."
        citation = f.get("legal_citation") or f.get("citation") or "-"
        rows.append(
            {
                "Kategori": f.get("category", "-"),
                "Soru": f.get("question", "-"),
                "Özet Cevap": ans_short,
                "Resmî Yasal Dayanak": citation,
            }
        )
    return pd.DataFrame(rows)



def build_ui() -> gr.Blocks:
    """9 Sekmeli Modern Gradio Arayüzünü İnşa Eder."""
    with gr.Blocks(title="TarımDestekRAG 2026") as app:
        # Üst Banner
        gr.HTML("""
        <div class="hero-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1>🌾 TarımDestekRAG — 2026 Bitkisel Üretim Destekleri</h1>
                    <p>Deterministik Kural Motoru, Doğrudan Resmî Atıflar ve Çiftçi Destek Karar Asistanı</p>
                    <span class="badge-tag">Kural Tabanlı Ön Değerlendirme &middot; Mevzuat Doğrulaması Devam Ediyor</span>
                </div>
                <div style="text-align: right; font-size: 0.9rem; opacity: 0.9;">
                    <div><b>Sürüm:</b> v1.0.0 (PC Sürümü)</div>
                    <div><b>Telif:</b> (c) 2026 Seydi Eryılmaz</div>
                </div>
            </div>
        </div>
        """)

        with gr.Tabs():
            # ================= SEKME 1 & 2: ÇİFTÇİ & PARSEL GİRİŞİ =================
            with gr.TabItem("🌱 Profil & Parsel Girişi", id="tab_inputs"):
                with gr.Row():
                    # Çiftçi Profili
                    with gr.Column(scale=1):
                        gr.Markdown("### 👤 1. Çiftçi Profili")
                        in_province = gr.Dropdown(
                            label="İl",
                            choices=PROVINCES,
                            value="KONYA",
                            allow_custom_value=True,
                        )
                        in_district = gr.Dropdown(
                            label="İlçe",
                            choices=DISTRICTS["KONYA"],
                            value="KARATAY",
                            allow_custom_value=True,
                        )

                        def update_districts(prov: str):
                            choices = DISTRICTS.get(prov, ["MERKEZ"])
                            return gr.Dropdown(choices=choices, value=choices[0])

                        in_province.change(
                            update_districts, inputs=[in_province], outputs=[in_district]
                        )

                        in_cks = gr.Radio(
                            label="Çiftçi Kayıt Sistemi (ÇKS) Durumu",
                            choices=[
                                "✅ Evet (ÇKS Kaydım Aktif)",
                                "❌ Hayır (ÇKS Kaydım Yok)",
                                "❓ Bilmiyorum / Emin Değilim",
                            ],
                            value="✅ Evet (ÇKS Kaydım Aktif)",
                        )
                        in_age = gr.Radio(
                            label="Yaş Durumu",
                            choices=["Genç Çiftçi (< 41 Yaş)", "Standart (41+ Yaş)"],
                            value="Genç Çiftçi (< 41 Yaş)",
                        )
                        in_gender = gr.Radio(
                            label="Cinsiyet",
                            choices=["Erkek", "Kadın Çiftçi"],
                            value="Erkek",
                        )

                    # Parsel & Ürün Bilgileri
                    with gr.Column(scale=1):
                        gr.Markdown("### 🚜 2. Parsel & Ürün Bilgisi")
                        in_crop = gr.Dropdown(
                            label="Ekilmiş / Planlanan Ürün",
                            choices=CROPS,
                            value="BUĞDAY",
                            allow_custom_value=True,
                            filterable=True,
                        )
                        in_area = gr.Number(
                            label="Parsel Alanı (Dekar / da)",
                            value=25.0,
                            minimum=0.1,
                            maximum=10000.0,
                            step=1.0,
                        )
                        in_irrigation = gr.Radio(
                            label="Sulama Türü",
                            choices=["Kuru Tarım", "Sulu Tarım", "❓ Bilmiyorum / Emin Değilim"],
                            value="Kuru Tarım",
                        )
                        in_seed_cert = gr.Radio(
                            label="Sertifikalı Tohum Faturası / Beyanı",
                            choices=[
                                "✅ Evet (Faturalı / Sertifikalı)",
                                "❌ Hayır (Sertifikasız Tohum)",
                                "❓ Bilmiyorum / Emin Değilim",
                            ],
                            value="✅ Evet (Faturalı / Sertifikalı)",
                        )
                        in_sapling_cert = gr.Radio(
                            label="Sertifikalı Fidan Faturası / Beyanı",
                            choices=[
                                "✅ Evet (Faturalı / Sertifikalı)",
                                "❌ Hayır (Standart / Sertifikasız)",
                                "❓ Bilmiyorum / Emin Değilim",
                            ],
                            value="❌ Hayır (Standart / Sertifikasız)",
                        )
                        in_orchard = gr.Radio(
                            label="Kapama Meyve Bahçesi Tesisi",
                            choices=[
                                "Evet (Kapama Bahçe)",
                                "Hayır (Münferit / Tarla)",
                                "❓ Bilmiyorum / Emin Değilim",
                            ],
                            value="Hayır (Münferit / Tarla)",
                        )

                gr.Markdown("#### ⚡ Hızlı Örnek Test Senaryoları (Tek Tıkla Otomatik Doldur & Hesapla)")
                with gr.Row():
                    preset_1 = gr.Button("🌾 1. Konya Buğday (Genç, Tohum)", size="sm", variant="secondary")
                    preset_2 = gr.Button("🌰 2. Samsun Fındık (Fidan, Bahçe)", size="sm", variant="secondary")
                    preset_3 = gr.Button("🌾 3. Konya Arpa (Standart)", size="sm", variant="secondary")
                    preset_4 = gr.Button("💧 4. Konya Mercimek (Su Kısıtı)", size="sm", variant="secondary")
                    preset_5 = gr.Button("❌ 5. ÇKS Kaydı Yok (Ret)", size="sm", variant="secondary")
                    preset_6 = gr.Button("❓ 6. Bilmiyorum / Eksik Bilgi", size="sm", variant="secondary")

                btn_calculate = gr.Button(
                    "🎯 Destekleri ve Hak Edişi Hesapla",
                    variant="primary",
                    size="lg",
                )

                # Tab 1 Canlı Hesaplama Özeti (Butonun hemen altında anında gösterilir)
                out_inline = gr.HTML(
                    "<div style='margin-top: 16px; padding: 14px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 10px; color: #64748b; text-align: center;'>Bilgilerinizi girip yukarıdaki <b>'Destekleri ve Hak Edişi Hesapla'</b> butonuna basarak hak edişinizi hemen görebilirsiniz.</div>"
                )

            # ================= SEKME 3: DESTEKLERİM KARTLARI =================
            with gr.TabItem("📋 Desteklerim", id="tab_supports"):
                out_kpi = gr.HTML(
                    "<div class='kpi-container'><div class='kpi-card'><div class='kpi-title'>Tahmini Destek</div><div class='kpi-value'>Hesaplama Bekleniyor</div></div></div>"
                )
                out_cards = gr.HTML(
                    "<p style='color: #64748b;'>Lütfen profil ve parsel bilgilerini girip 'Hesapla' butonuna tıklayınız.</p>"
                )
                with gr.Row():
                    btn_report = gr.Button(
                        "📄 Bağımsız Ön Değerlendirme Raporu Oluştur & İndir (.md)",
                        variant="secondary",
                        size="sm",
                    )
                file_report = gr.File(label="İndirilebilir Ön Değerlendirme Raporu", visible=False)
                out_disclaimer = gr.HTML("")

            # ================= SEKME 4: DESTEK DETAY TABLOSU =================
            with gr.TabItem("🔍 Destek Detay & Hesaplama", id="tab_details"):
                gr.Markdown("### 📊 2026 Destekleme Kalemleri Detay Tablosu")
                out_table = gr.DataFrame(
                    headers=[
                        "Destek Programı",
                        "Durum",
                        "Birim Fiyat (TL/da)",
                        "Alan (da)",
                        "Tahmini Tutar",
                        "Hesaplama Formülü",
                        "Başvuru Dönemi",
                        "Dayanak",
                    ],
                    datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                    interactive=False,
                )

                gr.Markdown("### 📅 2026 Resmî Başvuru Takvimi & Açık Destek Pencereleri")
                gr.DataFrame(value=get_application_windows_table(), interactive=False)

                gr.Markdown("""
                ### 📁 Başvuru İçin Gerekli Belgeler Kontrol Listesi
                - ✅ **Çiftçi Kayıt Sistemi (ÇKS) Belgesi:** Güncel 2026 üretim yılı için İlçe Tarım Müdürlüğünden veya e-Devlet kapısından onaylı.
                - ✅ **Sertifikalı Tohum / Fidan Faturası:** Bakanlık yetkili tohum/fidan bayisinden alınmış kaşeli orijinal fatura ve etiket kopyası.
                - ✅ **Tapu / Kira / Muvafakatname:** Parselin mülkiyet veya intifa hakkını tevsik eden belge.
                - ✅ **Başvuru Dilekçesi & Taahhütname:** İlgili destekleme programı için standart form.
                """)

            # ================= SEKME 5: NEDEN? GEREKÇE & ATIF =================
            with gr.TabItem("📜 Neden? (Gerekçe & Atıflar)", id="tab_reasons"):
                gr.HTML("""
                <div class="legal-reader-container" style="margin-top: 4px; margin-bottom: 16px; border-left: 6px solid #047857;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #064e3b; font-size: 1.15rem;">
                            ⚖️ Kural İzleri ve Mevzuat Kaynakları
                        </h4>
                        <span class="doc-badge-tag doc-badge-pass">Sıfır LLM &middot; Kaynak Doğrulaması Gereklidir</span>
                    </div>
                    <p style="margin: 8px 0 12px 0; font-size: 0.92rem; color: #334155; line-height: 1.55;">
                        Bu sistemde üreticiye sunulan her karar, dekar başı hesaplama ve hak ediş gerekçesi doğrudan
                        <b>Resmî Gazete</b> ve <b>BÜGEM</b> mevzuatındaki orijinal metinle delillendirilir. İlgili kanun maddesindeki
                        şartlar ve ret gerekçeleri sistem tarafından <b>renk kodlarıyla işaretlenmiştir</b>.
                    </p>
                    <div class="legal-legend-bar" style="margin-bottom: 0;">
                        <span class="legend-item"><span class="legend-dot dot-pass"></span> 🟢 <b>Yeşil Vurgu:</b> Sağlanan Şartlar & Hak Kazanma Hükmü</span>
                        <span class="legend-item"><span class="legend-dot dot-fail"></span> 🔴 <b>Kırmızı Vurgu:</b> Ret Gerekçesi & Yasal Yasaklar</span>
                        <span class="legend-item"><span class="legend-dot dot-gold"></span> 🟡 <b>Kehribar Vurgu:</b> Birim Destek Tutarları & Katsayılar</span>
                        <span class="legend-item"><span class="legend-dot dot-ref"></span> 🔵 <b>Mavi Vurgu:</b> Resmî Gazete / Madde Numarası Dayanağı</span>
                    </div>
                </div>
                """)

                out_reasons = gr.Markdown(
                    "Hesaplama yapıldığında kural motorunun işletim gerekçeleri, sağlanan/sağlanamayan koşullar ve Resmî Gazete yasal madde atıfları burada listelenecektir."
                )

                with gr.Accordion("📖 Resmî Mevzuat Metni ve Belge Önizleme Paneli (Doğrudan Resmî Gazete & BÜGEM)", open=True):
                    gr.Markdown("Aşağıdaki listeden incelemek istediğiniz maddeyi seçiniz. Resmî belgedeki şartlar, hak kazanma hükümleri ve ret gerekçeleri **renkli olarak işaretlenmiştir**:")
                    article_selector = gr.Dropdown(
                        choices=[
                            "MADDE 1 - Temel Destek ve ÇKS Zorunluluğu",
                            "MADDE 2 - Tarım Havzaları Planlı Üretim Desteği",
                            "MADDE 3 - Sertifikalı Tohum Kullanım Desteği",
                            "MADDE 4 - Yeraltı Su Kısıtı Olan Havzalar Desteği",
                            "MADDE 5 - Kadın ve Genç Çiftçi İlave Desteği",
                            "MADDE 6 - Sertifikalı Fidan ve Kapama Bahçe Şartı",
                            "EK TABLO - Ürün Bazlı Birim Fiyat Kataloğu",
                        ],
                        value="MADDE 1 - Temel Destek ve ÇKS Zorunluluğu",
                        label="İncelenecek Resmî Mevzuat Maddesi",
                    )

                    article_display = gr.HTML(
                        value=render_document_viewer_html("MADDE 1")
                    )

                    def update_article_view(choice: str) -> str:
                        return render_document_viewer_html(choice)

                    article_selector.change(update_article_view, inputs=[article_selector], outputs=[article_display])

            # ================= SEKME 6: CHATBOT (SORU-CEVAP) =================
            with gr.TabItem("💬 Soru-Cevap Asistanı", id="tab_chat"):
                gr.Markdown("""
                ### 🌾 2026 Tarımsal Destek Mevzuat ve Hak Ediş Asistanı (Sıfır LLM - Doğrulanmış Kararlar)
                Sorunuzu doğrudan doğal dille yazın. Sistem yürürlükteki 2026 Resmî Gazete destekleme mevzuatı,
                5488 sayılı Tarım Kanunu, ÇKS yönetmeliği ve mevcut veritabanından kaynaklı ön bilgi sunar; güncel mevzuatla bağımsız teyit edilmelidir.
                """)
                chatbot = gr.Chatbot(height=420, label="Mevzuat & Soru-Cevap Sohbeti")
                with gr.Row():
                    chat_input = gr.Textbox(
                        placeholder="Örn: 'Destekleme parasına haciz konulur mu?', 'Kiralık arazide ÇKS olur mu?', '2026 Buğday desteği ne kadar?'",
                        scale=8,
                        show_label=False,
                    )
                    chat_submit = gr.Button("Sor 🚀", scale=2, variant="primary")
                    chat_clear = gr.Button("🗑️ Temizle", scale=1, variant="secondary")

                gr.Markdown("**💡 En Sık Sorulan Çiftçi Soruları (Tek Tıkla Sor):**")
                with gr.Row():
                    q1 = gr.Button("🌾 2026 Buğday & Arpa Destek Tutarları", size="sm")
                    q2 = gr.Button("📑 ÇKS Kaydı Nasıl Yapılır & Evraklar", size="sm")
                    q3 = gr.Button("👩‍🌾 Kadın ve Genç Çiftçi İlave Desteği", size="sm")
                with gr.Row():
                    q4 = gr.Button("🚫 Destekleme Parasına Haciz Konur mu?", size="sm")
                    q5 = gr.Button("📝 Kiralık Arazide ÇKS ve Destek Alınır mı?", size="sm")
                    q6 = gr.Button("🤝 Hisseli Tapuda İmza Vermeyen Hissedar", size="sm")
                with gr.Row():
                    q7 = gr.Button("💧 Yeraltı Su Kısıtı Olan Havzalar Desteği", size="sm")
                    q8 = gr.Button("🌿 Organik Tarım & Biyolojik Mücadele", size="sm")
                    q9 = gr.Button("🔄 2026 Yeni Destek Modelinde Ne Değişti?", size="sm")
                with gr.Row():
                    q10 = gr.Button("🌱 Sertifikalı Tohum & Fidan Şartları", size="sm")
                    q11 = gr.Button("⚖️ Askı İcmali Nedir & 5 Günlük İtiraz", size="sm")
                    q12 = gr.Button("💳 Destekler Ne Zaman & Nereye Yatar?", size="sm")
                with gr.Row():
                    q13 = gr.Button("🐛 Kahverengi Kokarca & Zirai Mücadele", size="sm")
                    q14 = gr.Button("🛡️ TARSİM Sigortası & Don İhbar Süresi", size="sm")
                    q15 = gr.Button("☀️ Güneş Enerjisi (GES) & Sulama Hibesi", size="sm")

                with gr.Accordion("📚 2026 Resmî Çiftçi Sıkça Sorulan Sorular (SSS) Kütüphanesi & Rehberi", open=True):
                    gr.Markdown("Aşağıdaki resmi SSS tablosundan merak ettiğiniz konuyu seçip doğrudan asistana sorabilir veya arama yapabilirsiniz:")
                    faq_banner_md = gr.Markdown(get_faq_banner_text())
                    with gr.Row():
                        faq_cat_dropdown = gr.Dropdown(
                            choices=get_faq_categories(),
                            value="Tümü",
                            label="Kategoriye Göre Filtrele",
                            scale=4,
                        )
                        faq_search_input = gr.Textbox(
                            placeholder="Anahtar kelimeyle ara (haciz, kira, kokarca, tarsim, hibe, organik)...",
                            label="SSS Kütüphanesinde Ara",
                            scale=6,
                        )
                        btn_filter_faq = gr.Button("🔍 Filtrele / Ara", scale=2, variant="secondary")

                    faq_df = gr.DataFrame(value=get_faq_table(), interactive=False)

                    def update_faq_view(cat: str, search_txt: str) -> tuple[pd.DataFrame, str]:
                        table = get_faq_table(cat, search_txt)
                        banner = get_faq_banner_text()
                        return table, banner

                    faq_cat_dropdown.change(update_faq_view, inputs=[faq_cat_dropdown, faq_search_input], outputs=[faq_df, faq_banner_md])
                    btn_filter_faq.click(update_faq_view, inputs=[faq_cat_dropdown, faq_search_input], outputs=[faq_df, faq_banner_md])
                    faq_search_input.submit(update_faq_view, inputs=[faq_cat_dropdown, faq_search_input], outputs=[faq_df, faq_banner_md])

                    def on_faq_click(evt: gr.SelectData, df: pd.DataFrame, history: list[dict[str, str]]):
                        if evt is not None and hasattr(evt, "index"):
                            row_idx = evt.index[0]
                            if row_idx < len(df):
                                q_val = str(df.iloc[row_idx]["Soru"])
                                return ask_assistant(q_val, history)
                        return "", history

                    faq_df.select(
                        on_faq_click,
                        inputs=[faq_df, chatbot],
                        outputs=[chat_input, chatbot],
                    )

                chat_submit.click(
                    ask_assistant,
                    inputs=[chat_input, chatbot],
                    outputs=[chat_input, chatbot],
                )
                chat_input.submit(
                    ask_assistant,
                    inputs=[chat_input, chatbot],
                    outputs=[chat_input, chatbot],
                )
                chat_clear.click(lambda: ("", []), outputs=[chat_input, chatbot])

                # Hızlı Buton Bağlantıları
                def make_quick_ask(prompt: str):
                    def _h(history: list[dict[str, str]] | None = None):
                        return ask_assistant(prompt, history or [])
                    return _h

                q1.click(make_quick_ask("2026 yılında buğday ve arpa desteği ne kadar?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q2.click(make_quick_ask("ÇKS kaydı nasıl yapılır ve başvuru için hangi evraklar gerekir?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q3.click(make_quick_ask("Kadın çiftçilere ve genç çiftçilere ilave destek var mı?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q4.click(make_quick_ask("Tarımsal destekleme ödemelerine banka borcundan veya icradan haciz konulabilir mi?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q5.click(make_quick_ask("Kiralık arazide ÇKS kaydı ve tarımsal destek alınabilir mi?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q6.click(make_quick_ask("Hisseli tapulu arazide diğer hissedarlar imza vermezse ÇKS nasıl yapılır?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q7.click(make_quick_ask("Yeraltı su kısıtı olan havzalar desteği nedir ve hangi ürünlere verilir?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q8.click(make_quick_ask("Organik tarım ve biyolojik mücadele desteği kimlere verilir?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q9.click(make_quick_ask("2026 Yeni Destekleme Modeli'nde eski sisteme göre ne değişti?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q10.click(make_quick_ask("Sertifikalı tohum ve sertifikalı fidan destekleme şartları nelerdir?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q11.click(make_quick_ask("Askı icmali nedir, kaç gün askıda kalır ve itiraz süresi ne kadardır?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q12.click(make_quick_ask("Tarımsal destekleme ödemeleri ne zaman ve hangi bankaya yatar?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q13.click(make_quick_ask("Kahverengi kokarca zararlısıyla nasıl mücadele edilir ve ilaçlama desteği var mı?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q14.click(make_quick_ask("TARSİM tarım sigortasında don ve kuraklık hasarı ihbar süresi kaç gündür?"), inputs=[chatbot], outputs=[chat_input, chatbot])
                q15.click(make_quick_ask("Tarımsal sulamada güneş enerjisi (GES) ve modern damla sulama için hibe desteği var mı?"), inputs=[chatbot], outputs=[chat_input, chatbot])


            # ================= SEKME 7: SCRAPER PANELI =================
            with gr.TabItem("🌐 Mevzuat & Kazıyıcı Paneli", id="tab_scraper"):
                gr.Markdown("### 📡 Takip Edilen Resmî Mevzuat Kaynakları")
                sources_df = gr.DataFrame(value=get_sources_table(), interactive=False)
                with gr.Row():
                    btn_refresh_sources = gr.Button("🔄 Kaynakları Yenile", size="sm")
                btn_refresh_sources.click(get_sources_table, outputs=[sources_df])

                gr.Markdown("""
                #### 🔄 Otomatik Değişiklik Algılama & Hash Sistemi
                - Her resmî kaynak URL'si düzenli aralıklarla kontrol edilir.
                - İçerik SHA-256 kanonik hash'i alınarak sürüm tablosuna kaydedilir (`source_versions`).
                - Mevzuat değiştiğinde sistem uyarı üretir ve değişiklik logu tutar.
                """)

                gr.Markdown("---")
                gr.Markdown("### 🌾 Tarımsal Soru-Cevap Bilgi Tabanı & Web Harvester (Tüm Tarımsal Konular)")
                gr.Markdown("""
                Tarım ve Orman Bakanlığı, BÜGEM, TAGEM Zirai Mücadele, TARSİM Sigortası, TKDK IPARD ve Ziraat Odaları gibi resmî kurumsal
                portal ve rehberlerden soru-cevap veri setini çeker, SQLite veritabanına işler ve arama vektör indeksine (Hybrid BM25 + FAISS) canlı entegre eder.
                """)
                with gr.Row():
                    btn_harvest_faqs = gr.Button("Yerleşik SSS Verisini Yenile (Yönetici)", variant="secondary", interactive=False)
                harvest_status_box = gr.Markdown("**Bilgi:** Web üzerinden canlı SSS taraması henüz uygulanmadı. Yerleşik örnek veriyi yeniden yükleyen yönetici API'si varsayılan olarak kapalıdır. Bu ekran yeni mevzuatı otomatik olarak güncellemez.")

                def on_harvest_click() -> str:
                    res = api_client.harvest_faqs()
                    if res.get("status") == "SUCCESS":
                        cnt = res.get("harvested_count", 0)
                        tot = res.get("total_faqs_in_db", 0)
                        return f"✅ **Senkronizasyon Başarılı:** {cnt} yeni soru-cevap veritabanına işlendi ve RAG indeksine eklendi! (Toplam Veritabanı: **{tot} SSS**)."
                    return f"⚠️ **Bilgi:** {res.get('message', 'İşlem tamamlandı.')}"

                btn_harvest_faqs.click(on_harvest_click, outputs=[harvest_status_box])

            # ================= SEKME 8: BENCHMARK TABLOSU =================
            with gr.TabItem("📊 Doğrulama & Benchmark (100 Vaka)", id="tab_benchmark"):
                gr.Markdown("""
                ### 🧪 Deterministik Kural Motoru Benchmark Test Seti (100 Vaka)
                100 farklı çiftçi/parsel senaryosunda (ÇKS eksikliği, havza uyumsuzluğu, sertifikasız tohum vb.)
                bu bölüm kaydedilmiş test çıktılarını gösterir. Mevzuatla bağımsız uyum doğrulaması değildir.
                """)
                gr.DataFrame(value=load_benchmark_data(), interactive=False)
                gr.Markdown(get_benchmark_summary())

            # ================= SEKME 9: ADMIN & LİSANS =================
            with gr.TabItem("⚙️ Admin & Sistem Mimarisi", id="tab_admin"):
                gr.Markdown("""
                ### 🏛️ TarımDestekRAG Sistem Mimarisi & Geleneksel RAG'lardan Temel Farklar
                - **Sıfır LLM (Zero-LLM Güvencesi):** Hak ediş ve karar aşamalarında asla dış üretici model (OpenAI, Gemini vb.) kullanılmaz; kararlar `%100` deterministik Python kural motoru (`rules_impl.py`) tarafından yürütülür. Deterministik çıktının mevzuatla doğruluğu ayrıca test edilmelidir.
                - **Hassas Finansal Matematik:** Tüm parasal destek hesaplamaları Python `decimal.Decimal` ile kuruş hassasiyetinde yapılır. Kayan nokta yuvarlama hatası bulunmaz.
                - **Kaynak Provenansı (Geliştirilmekte):** Yalnızca Resmî Gazete, BÜGEM ve DSİ'nin yasal metinleri baz alınır. Her kaynak URL'si SHA-256 kanonik hash kontrolüyle izlenir.
                - **Belge İçi Renkli İşaretleme Sistemi:** Hak kazanma hükümleri 🟢 yeşil, ret ve yasak hükümleri 🔴 kırmızı, birim tutarlar 🟡 kehribar ve yasal merciler 🔵 mavi ile işaretlenerek kullanıcıya mutlak şeffaflık sunulur.
                - **Hibrit Arama Motoru:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` + `FAISS` ve `BM25Plus` ile Reciprocal Rank Fusion birleşimi (MRR=1.0000).
                - **Çok Platformlu Hazırlık:** Arka uç FastAPI bağımsız REST API olarak çalışır; Web, PC ve Flutter mobil uygulaması aynı çekirdeği paylaşır.

                ---
                ### 📜 Telif Hakkı ve Lisans Bildirimi
                ```
                ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
                Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

                Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
                amaçlı olarak paylaşılmıştır.

                YASAKLAR:
                  1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
                  2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
                  3. Alt lisanslanamaz, satılamaz veya devredilemez.
                  4. Tersine mühendislik yapılamaz.

                İZİN VERİLEN KULLANIM:
                  - GitHub üzerinde görüntüleme ve okuma.
                  - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

                YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
                İzin talepleri için: GitHub @seydivakkas
                ```
                """)

        # Girdi ve Çıktı Bileşen Listeleri
        inputs_list = [
            in_province,
            in_district,
            in_cks,
            in_age,
            in_gender,
            in_crop,
            in_area,
            in_irrigation,
            in_seed_cert,
            in_sapling_cert,
            in_orchard,
        ]
        calc_outputs = [out_kpi, out_cards, out_table, out_reasons, out_disclaimer, out_inline]

        # Değerlendirme Butonu Bağlantısı
        btn_calculate.click(
            evaluate_farmer_parcel,
            inputs=inputs_list,
            outputs=calc_outputs,
        )

        # Hızlı Örnek Test Senaryoları (Tek tıkla değerleri doldur ve anında hesapla)
        preset_1.click(
            lambda: (
                "KONYA", "KARATAY", "✅ Evet (ÇKS Kaydım Aktif)", "Genç Çiftçi (< 41 Yaş)", "Erkek",
                "BUĞDAY", 25.0, "Kuru Tarım", "✅ Evet (Faturalı / Sertifikalı)", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(evaluate_farmer_parcel, inputs=inputs_list, outputs=calc_outputs)

        preset_2.click(
            lambda: (
                "SAMSUN", "ÇARŞAMBA", "✅ Evet (ÇKS Kaydım Aktif)", "Standart (41+ Yaş)", "Kadın Çiftçi",
                "FINDIK", 15.0, "Kuru Tarım", "❌ Hayır (Sertifikasız Tohum)", "✅ Evet (Faturalı / Sertifikalı)", "Evet (Kapama Bahçe)",
            ),
            outputs=inputs_list,
        ).then(evaluate_farmer_parcel, inputs=inputs_list, outputs=calc_outputs)

        preset_3.click(
            lambda: (
                "KONYA", "KARATAY", "✅ Evet (ÇKS Kaydım Aktif)", "Standart (41+ Yaş)", "Erkek",
                "ARPA", 30.0, "Kuru Tarım", "✅ Evet (Faturalı / Sertifikalı)", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(evaluate_farmer_parcel, inputs=inputs_list, outputs=calc_outputs)

        preset_4.click(
            lambda: (
                "KONYA", "KARATAY", "✅ Evet (ÇKS Kaydım Aktif)", "Genç Çiftçi (< 41 Yaş)", "Erkek",
                "MERCİMEK", 20.0, "Kuru Tarım", "❌ Hayır (Sertifikasız Tohum)", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(evaluate_farmer_parcel, inputs=inputs_list, outputs=calc_outputs)

        preset_5.click(
            lambda: (
                "KONYA", "KARATAY", "❌ Hayır (ÇKS Kaydım Yok)", "Standart (41+ Yaş)", "Erkek",
                "BUĞDAY", 10.0, "Kuru Tarım", "❌ Hayır (Sertifikasız Tohum)", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(evaluate_farmer_parcel, inputs=inputs_list, outputs=calc_outputs)

        preset_6.click(
            lambda: (
                "KONYA", "KARATAY", "❓ Bilmiyorum / Emin Değilim", "Standart (41+ Yaş)", "Erkek",
                "BUĞDAY", 20.0, "Kuru Tarım", "❓ Bilmiyorum / Emin Değilim", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(evaluate_farmer_parcel, inputs=inputs_list, outputs=calc_outputs)

        # Resmî Ön Değerlendirme Raporu Oluşturma
        btn_report.click(
            generate_evaluation_report,
            inputs=inputs_list,
            outputs=[file_report],
        )

    return app


if __name__ == "__main__":
    app_instance = build_ui()
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    theme = get_tarim_theme()
    app_instance.launch(
        server_name="127.0.0.1",
        server_port=server_port,
        theme=theme,
        css=CUSTOM_CSS,
        share=False,
    )
