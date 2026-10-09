"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import os
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = r"C:\Windows\Fonts\comicbd.ttf"
BASE_DIR = r"c:\Users\seydieryilmaz\TarımRAGProje"
BRAIN_DIR = r"C:\Users\seydieryilmaz\.gemini\antigravity-ide\brain\1c7353b9-b1b4-43fe-90d9-0d5f5a42a50e"

# Color constants
WHITE = (255, 255, 255)
BLACK = (25, 25, 25)
RED = (175, 42, 42)
BLUE = (35, 88, 165)
ORANGE = (216, 115, 26)
GREEN_VALVE = (35, 155, 55)
ORANGE_VALVE = (215, 125, 20)
RED_VALVE = (195, 35, 35)

def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)

def draw_centered_text(draw, box, lines, font, color, line_spacing=4, clear_bg=True, fill_color=WHITE):
    """
    box: (x1, y1, x2, y2)
    lines: list of strings
    """
    x1, y1, x2, y2 = box
    if clear_bg:
        draw.rectangle([x1, y1, x2, y2], fill=fill_color)
    
    line_bboxes = [font.getbbox(line) for line in lines]
    line_heights = [bb[3] - bb[1] for bb in line_bboxes]
    line_widths = [bb[2] - bb[0] for bb in line_bboxes]
    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
    
    box_w = x2 - x1
    box_h = y2 - y1
    
    start_y = y1 + (box_h - total_height) / 2
    cur_y = start_y
    for i, line in enumerate(lines):
        w = line_widths[i]
        x = x1 + (box_w - w) / 2
        draw.text((x, cur_y - line_bboxes[i][1]), line, font=font, fill=color)
        cur_y += line_heights[i] + line_spacing

def render_fullstack():
    img_path = os.path.join(BRAIN_DIR, "fullstack_architecture_xiaohei_1791543400154.jpg")
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # 1. Top Left: WEB KULLANICI ARAYÜZÜ (above browser)
    draw_centered_text(draw, (75, 240, 330, 275), ["WEB KULLANICI ARAYÜZÜ"], get_font(16), BLACK)

    # 2. Subhead: KULLANICI PANELİ (below browser)
    draw_centered_text(draw, (95, 545, 275, 578), ["KULLANICI PANELİ"], get_font(15), BLACK)

    # 3. Red note: EL ÇİZİMİ VURGULAR (bottom left)
    draw_centered_text(draw, (80, 610, 245, 665), ["EL ÇİZİMİ", "VURGULAR"], get_font(13), RED, line_spacing=2)

    # 4. DATA FLOW -> VERİ AKIŞI (above blue arrow to Xiaohei, x=355..435, y=198..255)
    draw_centered_text(draw, (355, 198, 435, 255), ["VERİ", "AKIŞI"], get_font(13), BLACK, line_spacing=2)

    # 5. PROCESS top -> İŞLEM (above lever handle)
    draw_centered_text(draw, (430, 294, 520, 324), ["İŞLEM"], get_font(13), BLACK)

    # 6. PROCESS bottom -> İŞLEM (on pipe below lever)
    draw_centered_text(draw, (445, 500, 535, 530), ["İŞLEM"], get_font(13), BLACK)

    # 7. SECURITY LAYER bottom -> GÜVENLİK KATMANI (with up arrow)
    draw_centered_text(draw, (410, 600, 520, 652), ["GÜVENLİK", "KATMANI"], get_font(12), BLACK, line_spacing=2)

    # 8. BITEMPORAL CLOCK top -> ÇİFT ZAMANLI SAAT (above clock)
    draw_centered_text(draw, (530, 272, 665, 328), ["ÇİFT ZAMANLI", "SAAT"], get_font(13), BLACK, line_spacing=2)

    # 9. VALID FROM -> YÜRÜRLÜK BAŞLANGICI (left of clock, exact box covering VALID FROM completely)
    draw_centered_text(draw, (505, 340, 568, 388), ["YÜRÜRLÜK", "BAŞLANGICI"], get_font(8), BLACK, line_spacing=2)

    # 10. VALID TO -> YÜRÜRLÜK BİTİŞİ (right of clock)
    draw_centered_text(draw, (620, 340, 680, 388), ["YÜRÜRLÜK", "BİTİŞİ"], get_font(9), BLACK, line_spacing=2)

    # 11. RECORDED AT -> YAYIM TARİHİ (clock bottom right)
    draw_centered_text(draw, (570, 526, 680, 554), ["YAYIM TARİHİ"], get_font(10), BLACK)

    # 12. BITEMPORAL CLOCK bottom -> BİTEMPORAL ZAMAN MOTORU (below clock)
    draw_centered_text(draw, (530, 554, 665, 600), ["BİTEMPORAL", "ZAMAN MOTORU"], get_font(12), BLACK, line_spacing=2)

    # 13. SECURITY LAYER top -> GÜVENLİK KATMANI (above arrow to vault)
    draw_centered_text(draw, (665, 204, 775, 255), ["GÜVENLİK", "KATMANI"], get_font(12), BLACK, line_spacing=2)

    # 14. DUAL-KEY NOTARY VAULT -> ÇİFT ONAYLI NOTER KASASI (above vault)
    draw_centered_text(draw, (720, 295, 835, 372), ["ÇİFT ONAYLI", "NOTER KASASI"], get_font(13), BLACK, line_spacing=2)

    # 15. AUDIT TRAIL top -> DENETİM İZİ (above arrow to valve)
    draw_centered_text(draw, (815, 238, 885, 288), ["DENETİM", "İZİ"], get_font(12), BLACK, line_spacing=2)

    # 16. Tech & Legal keys (between figures, exact box y=520..560 wiping out Tech & Legal completely)
    draw_centered_text(draw, (715, 520, 775, 558), ["Teknik"], get_font(12), BLACK)
    draw_centered_text(draw, (780, 520, 840, 558), ["Hukuk"], get_font(12), BLACK)

    # 17. NOTARY VAULT bottom -> NOTER KASASI (below notary figures)
    draw_centered_text(draw, (700, 595, 860, 628), ["NOTER KASASI"], get_font(14), BLACK)

    # 18. TRI-STATE VALVE top -> ÜÇ KONUMLU VANA (above valve wheel)
    draw_centered_text(draw, (900, 275, 1015, 328), ["ÜÇ KONUMLU", "VANA"], get_font(13), BLACK, line_spacing=2)

    # 19. Valve internal labels (inside lens, clear old text and draw Turkish)
    draw_centered_text(draw, (925, 408, 1015, 435), ["UYGUN"], get_font(12), GREEN_VALVE)
    draw_centered_text(draw, (925, 435, 1015, 464), ["İNCELEME"], get_font(11), ORANGE_VALVE)
    draw_centered_text(draw, (925, 464, 1015, 490), ["RET"], get_font(12), RED_VALVE)

    # 20. TRI-STATE VALVE bottom -> ÜÇ KONUMLU ŞALTER (below valve)
    draw_centered_text(draw, (900, 522, 1015, 575), ["ÜÇ KONUMLU", "ŞALTER"], get_font(13), BLACK, line_spacing=2)

    # 21. AUDIT TRAIL bottom -> DENETİM KÜTÜĞÜ (under arrow to monolith)
    draw_centered_text(draw, (970, 610, 1045, 655), ["DENETİM", "KÜTÜĞÜ"], get_font(12), BLACK, line_spacing=2)

    # 22. Ed25519 seal -> Ed25519 MÜHÜR (above HSM)
    draw_centered_text(draw, (1010, 92, 1115, 146), ["Ed25519", "MÜHÜR"], get_font(13), BLACK, line_spacing=2)

    # 23. HARDWARE HSM -> DONANIMSAL HSM KASASI (next to HSM)
    draw_centered_text(draw, (990, 170, 1115, 225), ["DONANIMSAL", "HSM KASASI"], get_font(13), BLACK, line_spacing=2)

    # 24. WORM on stone monolith (large engraved WORM)
    draw_centered_text(draw, (1090, 335, 1260, 386), ["WORM"], get_font(34), BLACK)

    # 25. Bottom Monolith: KIRILMAZ TAŞ MONOLİTİ
    draw_centered_text(draw, (1100, 600, 1285, 656), ["KIRILMAZ TAŞ", "MONOLİTİ"], get_font(13), BLACK, line_spacing=2)

    # Save outputs
    out_tanitim = os.path.join(BASE_DIR, "proje_tanıtım_resim", "Xiaohei_FullStack_Sistem_Mimarisi_TR.jpg")
    out_brain = os.path.join(BRAIN_DIR, "Xiaohei_FullStack_Sistem_Mimarisi_TR.jpg")
    out_art = os.path.join(BRAIN_DIR, "fullstack_mimari_turkce.jpg")
    
    os.makedirs(os.path.dirname(out_tanitim), exist_ok=True)
    im.save(out_tanitim, quality=96)
    im.save(out_brain, quality=96)
    im.save(out_art, quality=96)
    print("Full-Stack image rendered successfully:", out_tanitim)

def render_evidence_pipeline():
    img_path = os.path.join(BRAIN_DIR, "evidence_pipeline_xiaohei_1791543420068.jpg")
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # Clean any tiny yellow speck under tractor/table
    draw.rectangle([545, 650, 570, 675], fill=WHITE)

    # 1. Top Left: Resmî Gazete Mevzuat Belgeleri
    draw_centered_text(draw, (48, 162, 305, 264), ["Resmî Gazete", "Mevzuat Belgeleri"], get_font(20), RED, line_spacing=4)

    # 2. On Paper on Scale: RESMÎ GAZETE (Tilted text on paper sheet)
    draw.polygon([(102, 298), (145, 255), (188, 308), (145, 345)], fill=WHITE)
    txt_img = Image.new("RGBA", (140, 70), (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    f_paper = get_font(13)
    txt_draw.text((10, 5), "RESMÎ", font=f_paper, fill=BLACK)
    txt_draw.text((10, 24), "GAZETE", font=f_paper, fill=BLACK)
    rotated_txt = txt_img.rotate(24, resample=Image.Resampling.BICUBIC, expand=True)
    im.paste(rotated_txt, (98, 255), mask=rotated_txt)

    # 3. Bottom Left: Hassas Bayt Terazisi
    draw_centered_text(draw, (52, 565, 198, 646), ["Hassas", "Bayt Terazisi"], get_font(17), RED, line_spacing=4)

    # 4. Top Middle: Hibrit Arama Motoru (BM25 + Vektör Arama)
    y1, y2 = 162, 264
    x1, x2 = 340, 690
    draw.rectangle([x1, y1, x2, y2], fill=WHITE)
    f_title = get_font(20)
    f_sub = get_font(16)
    t1 = "Hibrit Arama Motoru"
    t2 = "(BM25 + Vektör Arama)"
    bb1 = f_title.getbbox(t1)
    bb2 = f_sub.getbbox(t2)
    h1 = bb1[3] - bb1[1]
    h2 = bb2[3] - bb2[1]
    tot_h = h1 + h2 + 6
    sy = y1 + (y2 - y1 - tot_h) / 2
    draw.text((x1 + (x2 - x1 - (bb1[2] - bb1[0])) / 2, sy - bb1[1]), t1, font=f_title, fill=BLUE)
    draw.text((x1 + (x2 - x1 - (bb2[2] - bb2[0])) / 2, sy + h1 + 6 - bb2[1]), t2, font=f_sub, fill=BLUE)

    # 5. Under Pipe: Doğrulanmış Parçalar
    draw_centered_text(draw, (240, 575, 335, 638), ["Doğrulanmış", "Parçalar"], get_font(15), BLUE, line_spacing=3)

    # 6. Under Machine Left: Doğrulanmış Metin (BM25 + Vektör)
    draw_centered_text(draw, (335, 575, 515, 665), ["Doğrulanmış Metin", "(BM25 + Vektör)"], get_font(14), BLUE, line_spacing=3)

    # 7. Under Machine Right: Tarımsal Kanıt Motoru
    draw_centered_text(draw, (525, 575, 745, 646), ["Tarımsal Kanıt", "Motoru"], get_font(17), BLACK, line_spacing=4)

    # 8. Top Speech: Xiaohei: Destek tutarlarını ve PDF koordinatlarını sarı kalemle açıklıyor
    draw_centered_text(draw, (778, 150, 1045, 264), ["Xiaohei: Destek tutarlarını", "ve PDF koordinatlarını", "sarı kalemle açıklıyor"], get_font(17), ORANGE, line_spacing=4)

    # 9. Under Table: Şeffaf Hesaplama Masası
    draw_centered_text(draw, (760, 575, 975, 672), ["Şeffaf Hesaplama", "Masası"], get_font(17), ORANGE, line_spacing=4)

    # 10. Top Right: Mahkeme Düzeyi Adli Arşiv Kasası
    draw_centered_text(draw, (1095, 172, 1338, 274), ["Mahkeme Düzeyi", "Adli Arşiv Kasası"], get_font(19), BLACK, line_spacing=4)

    # 11. Bottom Right under Safe: Kriptografik Balmumu Mühür
    draw_centered_text(draw, (1150, 565, 1326, 652), ["Kriptografik", "Balmumu Mühür"], get_font(16), RED, line_spacing=4)

    # Save outputs
    out_tanitim = os.path.join(BASE_DIR, "proje_tanıtım_resim", "Xiaohei_Hukuki_Delil_ve_Veri_Hatti_TR.jpg")
    out_brain = os.path.join(BRAIN_DIR, "Xiaohei_Hukuki_Delil_ve_Veri_Hatti_TR.jpg")
    out_art = os.path.join(BRAIN_DIR, "delil_hatti_turkce.jpg")
    
    os.makedirs(os.path.dirname(out_tanitim), exist_ok=True)
    im.save(out_tanitim, quality=96)
    im.save(out_brain, quality=96)
    im.save(out_art, quality=96)
    print("Evidence Pipeline image rendered successfully:", out_tanitim)

if __name__ == "__main__":
    render_fullstack()
    render_evidence_pipeline()
