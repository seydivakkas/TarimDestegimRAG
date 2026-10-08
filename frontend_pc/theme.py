"""TarımDestekRAG Gradio PC Frontend Özel Tema ve CSS Stilleri.

Tasarım felsefesi:
- Canlı ve modern tarım/ekoloji renk paleti (Zümrüt yeşili, buğday altını, arduvaz grisi)
- Yüksek kontrast, okunabilir tipografi ve temiz kart yerleşimleri
- Göze çarpan durum rozetleri (Uygun: Yeşil, İnceleme: Sarı, Uygun Değil: Kırmızı)
"""

import gradio as gr

CUSTOM_CSS = """
/* Genel Kök Değişkenler ve Yazı Tipi */
:root {
    --primary-green: #15803d;
    --primary-light: #f0fdf4;
    --accent-gold: #d97706;
    --text-dark: #0f172a;
    --border-subtle: #e2e8f0;
}

body, .gradio-container {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
        Roboto, Arial, sans-serif !important;
}

/* Başlık ve Banner */
.hero-header {
    background: linear-gradient(135deg, #064e3b 0%, #047857 50%, #059669 100%);
    color: white !important;
    padding: 24px 32px;
    border-radius: 16px;
    margin-bottom: 20px;
    box-shadow: 0 10px 25px -5px rgba(6, 78, 59, 0.25);
}

.hero-header h1 {
    color: #ffffff !important;
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    margin: 0 0 8px 0 !important;
    letter-spacing: -0.025em;
}

.hero-header p {
    color: #a7f3d0 !important;
    font-size: 1.05rem !important;
    margin: 0 !important;
    font-weight: 500;
}

.badge-tag {
    display: inline-block;
    background: rgba(255, 255, 255, 0.2);
    color: #ffffff;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-top: 10px;
    backdrop-filter: blur(4px);
}

/* KPI Kartları */
.kpi-container {
    display: flex;
    gap: 16px;
    margin: 16px 0;
}

.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    flex: 1;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    text-align: center;
    border-top: 4px solid var(--primary-green);
}

.kpi-title {
    font-size: 0.9rem;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 2.2rem;
    font-weight: 800;
    color: #0f172a;
}

.kpi-value.green {
    color: #15803d;
}

.kpi-value.gold {
    color: #b45309;
}

/* Durum Rozetleri */
.badge-eligible {
    background-color: #dcfce7;
    color: #166534;
    padding: 4px 12px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 0.85rem;
    display: inline-block;
    border: 1px solid #86efac;
}

.badge-review {
    background-color: #fef3c7;
    color: #92400e;
    padding: 4px 12px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 0.85rem;
    display: inline-block;
    border: 1px solid #fde68a;
}

.badge-ineligible {
    background-color: #fee2e2;
    color: #991b1b;
    padding: 4px 12px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 0.85rem;
    display: inline-block;
    border: 1px solid #fca5a5;
}

/* Destek Programı Kartları */
.support-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.support-card:hover {
    box-shadow: 0 8px 16px -2px rgba(0, 0, 0, 0.08);
}

.support-card.eligible {
    border-left: 6px solid #22c55e;
}

.support-card.review {
    border-left: 6px solid #f59e0b;
}

.support-card.ineligible {
    border-left: 6px solid #ef4444;
}

.disclaimer-box {
    background: #fffbeb;
    border: 1px solid #fef3c7;
    border-left: 5px solid #d97706;
    padding: 14px 18px;
    border-radius: 8px;
    font-size: 0.92rem;
    color: #78350f;
    margin-top: 16px;
}

.citation-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #3b82f6;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 0.9rem;
    color: #334155;
    margin: 8px 0;
}

/* Tab 1 Canlı Hesaplama Özeti Kartı */
.inline-summary-box {
    background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
    border: 2px solid #86efac;
    border-radius: 16px;
    padding: 22px 28px;
    margin-top: 24px;
    box-shadow: 0 10px 15px -3px rgba(22, 101, 52, 0.08);
}

.inline-summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #dcfce7;
    padding-bottom: 14px;
    margin-bottom: 16px;
}

.inline-summary-payout {
    font-size: 2.1rem;
    font-weight: 800;
    color: #15803d;
}

.inline-chips-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
    margin-top: 14px;
}

.inline-support-item {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.inline-support-item.eligible {
    border-left: 5px solid #22c55e;
}

.inline-support-item.review {
    border-left: 5px solid #f59e0b;
}

.inline-support-item.ineligible {
    border-left: 5px solid #ef4444;
}

/* 📜 Tıklanabilir Resmî Belge ve Mevzuat Bağlantıları */
.doc-link-item {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 10px !important;
    text-decoration: none !important;
    padding: 6px 14px !important;
    border-radius: 8px !important;
    background: #f8fafc !important;
    border: 1px solid #cbd5e1 !important;
    font-size: 0.93rem !important;
    margin: 4px 0 !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
}

.doc-link-item.doc-pass {
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
    color: #1e293b !important;
}

.doc-link-item.doc-pass:hover {
    background: #f0fdf4 !important;
    border-color: #16a34a !important;
    color: #15803d !important;
    transform: translateX(3px) !important;
    box-shadow: 0 4px 6px -1px rgba(22, 101, 52, 0.12) !important;
}

.doc-link-item.doc-fail {
    background: #fffafa !important;
    border-color: #fecaca !important;
    color: #7f1d1d !important;
}

.doc-link-item.doc-fail:hover {
    background: #fef2f2 !important;
    border-color: #dc2626 !important;
    color: #991b1b !important;
    transform: translateX(3px) !important;
    box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.12) !important;
}

.doc-link-item.doc-action {
    background: #f0f9ff !important;
    border-color: #bae6fd !important;
    color: #0369a1 !important;
}

.doc-link-item.doc-action:hover {
    background: #e0f2fe !important;
    border-color: #0284c7 !important;
    color: #075985 !important;
    transform: translateX(3px) !important;
    box-shadow: 0 4px 6px -1px rgba(2, 132, 199, 0.12) !important;
}

.doc-badge-tag {
    font-size: 0.78rem !important;
    background: #0284c7 !important;
    color: #ffffff !important;
    padding: 3px 10px !important;
    border-radius: 9999px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    white-space: nowrap !important;
    transition: all 0.2s ease !important;
}

.doc-badge-tag.doc-badge-pass {
    background: #16a34a !important;
}

.doc-badge-tag.doc-badge-fail {
    background: #dc2626 !important;
}

.doc-badge-tag.doc-badge-action {
    background: #0284c7 !important;
}

.doc-link-item:hover .doc-badge-tag {
    filter: brightness(1.1) !important;
    transform: scale(1.03) !important;
}

.doc-citation-header-link {
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
    color: #0f172a !important;
    text-decoration: none !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    padding: 4px 8px !important;
    border-radius: 6px !important;
    transition: all 0.15s ease !important;
}

.doc-citation-header-link:hover {
    color: #15803d !important;
    background: #f0fdf4 !important;
    text-decoration: underline !important;
}

.doc-citation-link {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    width: 100% !important;
    gap: 8px !important;
    color: #15803d !important;
    text-decoration: none !important;
    font-weight: 700 !important;
    font-size: 0.96rem !important;
    padding: 8px 12px !important;
    background: #f0fdf4 !important;
    border: 1px solid #86efac !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}

.doc-citation-link:hover {
    color: #047857 !important;
    background: #dcfce7 !important;
    border-color: #22c55e !important;
    box-shadow: 0 4px 6px -1px rgba(34, 197, 94, 0.15) !important;
    transform: translateX(2px) !important;
}

/* 🎨 Renkli Mevzuat ve Belge Metni Vurgulama Stilleri */
.legal-hl-pass, mark.legal-hl-pass {
    background: #dcfce7 !important;
    color: #14532d !important;
    padding: 2px 7px !important;
    border-radius: 5px !important;
    font-weight: 700 !important;
    border-bottom: 2.5px solid #22c55e !important;
    display: inline !important;
}

.legal-hl-fail, mark.legal-hl-fail {
    background: #fee2e2 !important;
    color: #7f1d1d !important;
    padding: 2px 7px !important;
    border-radius: 5px !important;
    font-weight: 700 !important;
    border-bottom: 2.5px solid #ef4444 !important;
    display: inline !important;
}

.legal-hl-gold, mark.legal-hl-gold {
    background: #fef3c7 !important;
    color: #78350f !important;
    padding: 2px 7px !important;
    border-radius: 5px !important;
    font-weight: 700 !important;
    border-bottom: 2.5px solid #d97706 !important;
    display: inline !important;
}

.legal-hl-ref, mark.legal-hl-ref {
    background: #e0f2fe !important;
    color: #0369a1 !important;
    padding: 2px 7px !important;
    border-radius: 5px !important;
    font-weight: 600 !important;
    border-bottom: 2.5px solid #0284c7 !important;
    display: inline !important;
}

/* 📖 Resmî Mevzuat Metni Belge Okuyucu & Kanıt Kartları */
.legal-reader-container {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
    padding: 22px 26px !important;
    margin-top: 14px !important;
    box-shadow: 0 4px 10px -2px rgba(15, 23, 42, 0.05) !important;
}

.legal-reader-header {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    border-bottom: 1px solid #e2e8f0 !important;
    padding-bottom: 12px !important;
    margin-bottom: 14px !important;
}

.legal-reader-title {
    margin: 0 0 4px 0 !important;
    color: #0f172a !important;
    font-size: 1.15rem !important;
    font-weight: 800 !important;
}

.legal-source-sub {
    font-size: 0.88rem !important;
    color: #64748b !important;
}

.legal-legend-bar {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 16px !important;
    padding: 10px 16px !important;
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    margin-bottom: 18px !important;
    font-size: 0.86rem !important;
}

.legend-item {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    color: #334155 !important;
}

.legend-dot {
    width: 10px !important;
    height: 10px !important;
    border-radius: 50% !important;
    display: inline-block !important;
}

.dot-pass { background-color: #22c55e !important; }
.dot-fail { background-color: #ef4444 !important; }
.dot-gold { background-color: #d97706 !important; }
.dot-ref  { background-color: #0284c7 !important; }

.legal-reader-paragraph {
    font-size: 0.98rem !important;
    line-height: 1.75 !important;
    color: #1e293b !important;
    margin-bottom: 14px !important;
    padding: 10px 14px !important;
    background: #fdfdfd !important;
    border-left: 3px solid #cbd5e1 !important;
    border-radius: 0 6px 6px 0 !important;
}

/* 📜 Renkli Kanıt Kartı (.legal-quote-card) */
.legal-quote-card {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-left: 6px solid #16a34a !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
    margin: 10px 0 14px 0 !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03) !important;
}

.legal-quote-card.pass {
    border-left-color: #16a34a !important;
    background: #fcfdfc !important;
}

.legal-quote-card.fail {
    border-left-color: #dc2626 !important;
    background: #fffafa !important;
}

.legal-quote-card.warn {
    border-left-color: #d97706 !important;
    background: #fffdf5 !important;
}

.legal-quote-header {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    margin-bottom: 8px !important;
    color: #475569 !important;
}

.legal-doc-badge {
    color: #0f172a !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
}

.legal-source-link {
    color: #0284c7 !important;
    text-decoration: none !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    background: #f0f9ff !important;
    padding: 3px 8px !important;
    border-radius: 4px !important;
    border: 1px solid #bae6fd !important;
    transition: all 0.2s ease !important;
}

.legal-source-link:hover {
    background: #e0f2fe !important;
    color: #0369a1 !important;
}

.legal-quote-body {
    font-size: 0.94rem !important;
    line-height: 1.65 !important;
    color: #1e293b !important;
}
"""



def get_tarim_theme() -> gr.Theme:
    """Yeşil tarımsal temayı üretir."""
    return gr.themes.Soft(
        primary_hue="emerald",
        secondary_hue="amber",
        neutral_hue="slate",
        spacing_size="sm",
        radius_size="md",
    )
