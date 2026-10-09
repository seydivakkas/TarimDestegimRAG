"""TarımDestekRAG PC Arayüzü Veri Biçimlendirme ve Sunum Yardımcıları."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd
from tarim_destek_rag.citations.document_links import (
    format_citation_section_header,
    format_clickable_action,
    format_clickable_check,
    format_highlighted_citation_card,
    resolve_check_link,
)

logger = logging.getLogger("frontend_pc.formatters")


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


def format_currency(val: float | int | str | None) -> str:
    """Türk Lirası para birimi biçimlendirici.

    None durumunda 'Hesaplanmadı', geçersiz durumlarda 'Doğrulama gerekli' döner.
    """
    if val is None:
        return "Hesaplanmadı"
    try:
        f_val = float(val)
        return f"{f_val:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "Doğrulama gerekli"


def calculate_window_status(
    start_str: str | None, end_str: str | None, is_active: bool
) -> tuple[str, str, str]:
    """Başvuru penceresi tarihlerine ve güncel yerel tarihe göre dinamik durum hesaplar."""
    if not start_str or not end_str:
        return "Belirtilmedi", "Belirtilmedi", "⚪ DOĞRULANMADI / BELİRTİLMEDİ"
    try:
        today = datetime.now().date()
        s_date = (
            datetime.strptime(start_str, "%Y-%m-%d").date()
            if "-" in start_str
            else datetime.strptime(start_str, "%d.%m.%Y").date()
        )
        e_date = (
            datetime.strptime(end_str, "%Y-%m-%d").date()
            if "-" in end_str
            else datetime.strptime(end_str, "%d.%m.%Y").date()
        )
        fmt_start = s_date.strftime("%d.%m.%Y")
        fmt_end = e_date.strftime("%d.%m.%Y")
        if not is_active:
            status = "🔴 PASİF"
        elif today < s_date:
            status = f"🟡 BAŞVURUYA YAKLAŞIYOR ({fmt_start})"
        elif s_date <= today <= e_date:
            status = "🟢 BAŞVURUYA AÇIK"
        else:
            status = f"🔴 BAŞVURU SÜRESİ DOLDU ({fmt_end})"
        return fmt_start, fmt_end, status
    except Exception:
        return start_str or "Doğrulanmadı", end_str or "Doğrulanmadı", "⚪ DOĞRULANMADI"


def render_inline_summary_html(
    resp: dict[str, Any] | None,
    area_da: float,
    crop: str,
    province: str,
    district: str,
) -> str:
    """Tab 1 Çiftçi & Parsellerim için anlık özet ve rozet kutusu üretir."""
    if not resp or "rules" not in resp:
        return (
            "<div style='margin-top: 16px; padding: 14px; background: #f8fafc; "
            "border: 1px dashed #cbd5e1; border-radius: 10px; color: #64748b; text-align: center;'>"
            "Bilgilerinizi girip yukarıdaki <b>'Destekleri ve Hak Edişi Hesapla'</b> butonuna "
            "basarak hak edişinizi hemen görebilirsiniz.</div>"
        )

    rules = resp.get("rules", [])
    calculations = resp.get("calculations", [])
    calc_map = {c.get("support_id"): c for c in calculations}
    total_payout = resp.get("total_estimated_amount", 0.0)

    effective_statuses = [
        calc_map.get(r.get("support_id"), {}).get("status", r.get("status"))
        for r in rules
    ]
    eligible_count = effective_statuses.count("ELIGIBLE")
    review_count = effective_statuses.count("REVIEW")
    ineligible_count = effective_statuses.count("NOT_ELIGIBLE")

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

    return f"""
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
            💡 <b>Ayrıntılı İnceleme:</b> Kart bazlı döküm, birim fiyat formülleri, renkli Resmî Gazete kanıt maddeleri ve ön değerlendirme raporu için lütfen <b>"📊 Destek Analizi"</b> sekmesine geçiniz.
        </div>
    </div>
    """


def render_kpi_html(resp: dict[str, Any] | None) -> str:
    """Tab 2 Destek Analizi için KPI kartları HTML'i üretir."""
    if not resp or "rules" not in resp:
        return (
            "<div class='kpi-container'>"
            "<div class='kpi-card'><div class='kpi-title'>Tahmini Destek</div>"
            "<div class='kpi-value'>Hesaplama Bekleniyor</div></div>"
            "</div>"
        )

    rules = resp.get("rules", [])
    calculations = resp.get("calculations", [])
    calc_map = {c.get("support_id"): c for c in calculations}
    total_payout = resp.get("total_estimated_amount", 0.0)

    effective_statuses = [
        calc_map.get(r.get("support_id"), {}).get("status", r.get("status"))
        for r in rules
    ]
    eligible_count = effective_statuses.count("ELIGIBLE")
    review_count = effective_statuses.count("REVIEW")
    ineligible_count = effective_statuses.count("NOT_ELIGIBLE")

    return f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-title">Toplam Tahmini Hak Ediş</div>
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


def render_support_cards_html(resp: dict[str, Any] | None) -> str:
    """Tab 2 Destek Analizi için destek kartları listesi HTML'i üretir."""
    if not resp or "rules" not in resp:
        return "<p style='color: #64748b;'>Lütfen 'Çiftçi & Parsellerim' sekmesinden parsel bilgilerinizi girip 'Destekleri ve Hak Edişi Hesapla' butonuna tıklayınız.</p>"

    rules = resp.get("rules", [])
    calculations = resp.get("calculations", [])
    explanations = resp.get("explanations", [])
    calc_map = {c.get("support_id"): c for c in calculations}
    exp_map = {e.get("support_id"): e for e in explanations}

    cards_html = "<div style='display: flex; flex-direction: column; gap: 14px; margin-top: 10px;'>"
    for ev in rules:
        sid = ev.get("support_id")
        sname = ev.get("support_name", sid)
        calc = calc_map.get(sid, {})
        status = calc.get("status", ev.get("status"))
        total_amt = calc.get("estimated_amount")
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

    cards_html += "</div>"
    return cards_html


def render_details_dataframe(
    resp: dict[str, Any] | None, area_da: float = 0.0
) -> pd.DataFrame:
    """Tab 2 Destek Analizi için detay hesaplama DataFrame tablosu üretir."""
    if not resp or "rules" not in resp:
        return pd.DataFrame(
            columns=[
                "Destek Programı",
                "Durum",
                "Birim Fiyat (TL/da)",
                "Alan (da)",
                "Tahmini Tutar",
                "Hesaplama Formülü",
                "Başvuru Dönemi",
                "Dayanak",
            ]
        )

    rules = resp.get("rules", [])
    calculations = resp.get("calculations", [])
    calc_map = {c.get("support_id"): c for c in calculations}

    table_rows = []
    for ev in rules:
        sid = ev.get("support_id")
        sname = ev.get("support_name", sid)
        calc = calc_map.get(sid, {})
        status = calc.get("status", ev.get("status"))
        total_amt = calc.get("estimated_amount")
        unit_amt = calc.get("unit_amount")
        formula = calc.get("formula", "-")

        if status == "ELIGIBLE":
            status_text = "ÖN DEĞERLENDİRME: UYGUN"
        elif status == "REVIEW":
            status_text = "İNCELEME / EKSİK BELGE"
        else:
            status_text = "UYGUN DEĞİL"

        table_rows.append(
            {
                "Destek Programı": sname,
                "Durum": status_text,
                "Birim Fiyat (TL/da)": (
                    f"{float(unit_amt):.2f} ₺"
                    if unit_amt is not None and float(unit_amt) > 0
                    else "Doğrulama gerekli"
                ),
                "Alan (da)": f"{area_da:.1f}",
                "Tahmini Tutar": format_currency(total_amt),
                "Hesaplama Formülü": formula,
                "Başvuru Dönemi": "Program bazında kaynak doğrulaması gerekli",
                "Dayanak": "Kaynak/sürüm kontrolü gerekli",
            }
        )

    return pd.DataFrame(table_rows)


def render_reasons_markdown(resp: dict[str, Any] | None) -> str:
    """Tab 2 Destek Analizi için kanıt zinciri ve işletim gerekçeleri markdown metni üretir."""
    if not resp or "rules" not in resp:
        return "Hesaplama yapıldığında kural motorunun işletim gerekçeleri, sağlanan/sağlanamayan koşullar ve Resmî Gazete yasal madde atıfları burada listelenecektir."

    rules = resp.get("rules", [])
    explanations = resp.get("explanations", [])
    exp_map = {e.get("support_id"): e for e in explanations}

    reasons_markdown = "### 📜 Kural Motoru İşletim Gerekçeleri ve Resmî Mevzuat Dayanakları\n\n"
    # Province + district + crop evidence is its own source-dependent finding.
    # It does not certify farmer eligibility or any payable amount.
    from html import escape
    from os import getenv

    basin = resp.get("basin_evidence")
    if isinstance(basin, dict) and basin.get("verification_status") == (
        "ORIGINAL_PDF_ROW_AND_CROP_LOCATED_DRAFT_REVIEW"
    ):
        link = str(basin.get("highlighted_pdf_url") or "")
        if link.startswith("/evidence/highlight/basin/"):
            public_api = getenv("API_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
            proof_link = escape(public_api + link, quote=True)
            original = escape(str(basin.get("source_url") or ""), quote=True)
            province = escape(str(basin.get("province") or ""))
            district = escape(str(basin.get("district") or ""))
            crop = escape(str(basin.get("crop_label") or ""))
            page = escape(str(basin.get("page_number") or ""))
            reasons_markdown += (
                "### 📍 Seçilen İlçe ve Ürün — Özgün Bakanlık PDF Kanıtı\n\n"
                f"**{province} / {district} — {crop}** · PDF sayfa {page}\n\n"
                f'<a href="{proof_link}" target="_blank" rel="noopener noreferrer">'
                "İlçeyi mavi, ürünü sarı işaretli PDF'de aç ↗</a> · "
                f'<a href="{original}" target="_blank" rel="noopener noreferrer">'
                "Değiştirilmemiş resmî PDF ↗</a>\n\n"
                "**Kaynak durumu:** İlçe/ürün satırı özgün PDF'de bulundu; "
                "satır henüz bağımsız uzman onaylı değildir ve tek başına "
                "destek uygunluğu/ödeme kanıtı değildir.\n\n---\n\n"
            )
    else:
        reasons_markdown += (
            "**İlçe/ürün kaynak kanıtı:** Seçilen ilçe ve ürün için özgün PDF'de "
            "birebir işaretleme şu anda doğrulanamadı (belge kurulmamış, "
            "ürün alt türü belirsiz veya kaynak yılı farklı olabilir).\n\n---\n\n"
        )
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
            first_cit_url = (
                citations[0].get("url") if isinstance(citations[0], dict) else None
            )
            reasons_markdown += (
                f"\n- {format_citation_section_header(first_cit_url)}:\n\n"
            )
            for cit in citations:
                reasons_markdown += f"{format_highlighted_citation_card(cit, status, sid)}\n\n"

        reasons_markdown += "\n---\n\n"

    return reasons_markdown


def render_disclaimer_html() -> str:
    """Yasal uyarı kutusu HTML'i."""
    return """
    <div class='disclaimer-box'>
        ⚖️ <b>Yasal Uyarı ve Sorumluluk Reddi:</b> Bu sistemde üretilen uygunluk durumları ve parasal tutarlar,
        Resmî Gazete'de yayımlanan 2026 bitkisel üretim destekleme mevzuatına dayalı <b>tahmini bir ön değerlendirmedir</b>.
        Kesin hak sahipliği, icmal listeleri ve ödemeler Tarım ve Orman Bakanlığı İl/İlçe Müdürlüklerinin yetkisindedir.
    </div>
    """


def generate_report_markdown(
    resp: dict[str, Any],
    farmer_data: dict[str, Any],
    parcel_data: dict[str, Any],
) -> str:
    """Bağımsız yazılımın resmî olmayan ön değerlendirme raporu metnini oluşturur."""
    total_payout = resp.get("total_estimated_amount", 0.0)
    rules = resp.get("rules", [])
    calculations = resp.get("calculations", [])
    explanations = resp.get("explanations", [])
    calc_map = {c.get("support_id"): c for c in calculations}
    exp_map = {e.get("support_id"): e for e in explanations}

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    parsed_cks = farmer_data.get("cks_status")
    parsed_seed = parcel_data.get("seed_certificate_available")
    parsed_sapling = parcel_data.get("sapling_certificate_available")
    parsed_orchard = parcel_data.get("is_closed_orchard")

    cks_txt = (
        "✅ Aktif / Kayıtlı"
        if parsed_cks is True
        else (
            "❌ Kayıt Bulunamadı"
            if parsed_cks is False
            else "❓ Bilinmiyor / Beyan Edilmedi (Ek İnceleme Gerekli)"
        )
    )
    seed_txt = (
        "✅ Mevcut / Faturalı"
        if parsed_seed is True
        else (
            "❌ Sertifikasız / Yok"
            if parsed_seed is False
            else "❓ Bilinmiyor / Beyan Edilmedi"
        )
    )
    sapling_txt = (
        "✅ Mevcut / Faturalı"
        if parsed_sapling is True
        else (
            "❌ Standart / Yok"
            if parsed_sapling is False
            else "❓ Bilinmiyor / Beyan Edilmedi"
        )
    )
    orchard_txt = (
        "Evet (Kapama Bahçe)"
        if parsed_orchard is True
        else (
            "Hayır"
            if parsed_orchard is False
            else "❓ Bilinmiyor / Beyan Edilmedi"
        )
    )

    province = farmer_data.get("province", "")
    district = farmer_data.get("district", "")
    gender = farmer_data.get("gender", "")
    age_group = farmer_data.get("age_group", "")
    area_da = float(parcel_data.get("area_da", 0.0))
    crop = parcel_data.get("crop", "")
    irrigation_type = parcel_data.get("irrigation", "")

    report_lines = [
        "# TarımDestekRAG — Bağımsız Bilgilendirme ve Tahmini Ön Değerlendirme Raporu (Bağımsız Yazılım Raporu)",
        "## 2026 Bitkisel Üretim Destekleri — Tahmini Ön Değerlendirme",
        "",
        "> [!IMPORTANT]",
        "> **YASAL UYARI VE BİLGİLENDİRME:** Bu belge Tarım ve Orman Bakanlığı tarafından düzenlenmiş veya onaylanmış resmî bir belge değildir. Bu rapor T.C. Tarım ve Orman Bakanlığı resmî belgesi, ödeme taahhüdü veya idari onay kararı DEĞİLDİR. Açık mevzuat kurallarına dayalı bir simülasyon ve bağımsız ön inceleme çıktısıdır.",
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
        f"- **Parsel Alanı:** {area_da:.1f} Dekar (da)",
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
            f"| {sname} | {st_tr} | {format_currency(uamt)}/da | {area_da:.1f} da | {format_currency(amt)} | 2026 Resmî Gazete |"
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

    return "\n".join(report_lines)
