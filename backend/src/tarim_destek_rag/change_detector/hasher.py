import hashlib
import re

from bs4 import BeautifulSoup


def canonicalize_html(raw_html: bytes | str) -> str:
    """HTML içeriğini gereksiz boşluk, script ve stil etiketlerinden arındırarak kanonikleştirir."""
    text = raw_html.decode("utf-8", errors="ignore") if isinstance(raw_html, bytes) else raw_html
    soup = BeautifulSoup(text, "html.parser")

    # Dinamik gürültü üreten etiketleri temizle
    for element in soup(["script", "style", "noscript", "iframe"]):
        element.decompose()

    # Yalnızca gövde metnini al veya temiz html'i al
    body_text = soup.get_text(separator=" ", strip=True)
    # Çoklu boşlukları ve satır sonlarını tek boşluğa indir
    canonical = re.sub(r"\s+", " ", body_text).strip()
    return canonical


def canonicalize_pdf(raw_pdf_bytes: bytes) -> bytes:
    """PDF için raw binary'den önce deterministik bayt akışı normalizasyonu."""
    # PDF meta-tag değişikliklerini önlemek için temel bayt kanonikleştirme
    return raw_pdf_bytes.strip()


def compute_content_hash(content: bytes | str, is_html: bool = False) -> str:
    """İçeriğin deterministik SHA-256 özetini (hash) hesaplar."""
    if is_html:
        canonical_str = canonicalize_html(content)
        data = canonical_str.encode("utf-8")
    elif isinstance(content, str):
        data = content.strip().encode("utf-8")
    else:
        data = canonicalize_pdf(content)

    return hashlib.sha256(data).hexdigest()
