"""Resmî Kaynak Kayıt Defteri ve URL İzin Listesi (Source Registry).

Tarım ve Orman Bakanlığı, Resmî Gazete ve Mevzuat Bilgi Sistemi haricindeki
alan adlarına tarama isteği yapılmasını engeller, SSRF ve güvenlik kontrollerini sağlar.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


class URLAllowlistRegistry:
    """Tarımsal mevzuat ve SSS kaynakları için güvenlik izin listesi."""

    ALLOWED_DOMAINS: frozenset[str] = frozenset({
        "tarimorman.gov.tr",
        "resmigazete.gov.tr",
        "mevzuat.gov.tr",
    })

    MAX_CONTENT_LENGTH: int = 5 * 1024 * 1024  # 5 MB
    REQUEST_TIMEOUT_SECONDS: float = 5.0
    MAX_RETRIES: int = 3
    USER_AGENT: str = "TarimDestekRAG-Bot/1.0 (+https://github.com/seydivakkas/TarimDestegimRAG)"

    @classmethod
    def is_url_allowed(cls, url: str) -> bool:
        """URL'nin izin verilen resmî kaynaklar listesinde olup olmadığını kontrol eder."""
        allowed, _ = cls.validate_url(url)
        return allowed

    @classmethod
    def validate_url(cls, url: str) -> tuple[bool, str]:
        """URL'yi şema, alan adı ve SSRF riskleri açısından ayrıntılı doğrular."""
        if not url or not isinstance(url, str):
            return False, "Boş veya geçersiz URL."

        try:
            parsed = urlparse(url.strip())
        except Exception as e:
            return False, f"URL çözümlenemedi: {e}"

        if parsed.scheme.lower() != "https":
            return False, "Güvenlik kuralı: Yalnızca HTTPS bağlantılarına izin verilir."

        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            return False, "URL alan adı içermiyor."

        # SSRF Koruması: Localhost veya özel IP bloklarını engelle
        if hostname == "localhost":
            return False, "SSRF Koruması: 'localhost' erişimi engellendi."

        try:
            ip_obj = ipaddress.ip_address(hostname)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
                return False, f"SSRF Koruması: Özel veya yerel IP adresine ({hostname}) erişim engellendi."
        except ValueError:
            # IP adresi değil, normal alan adı
            pass

        # İzinli alan adı son eki kontrolü (.tarimorman.gov.tr, .resmigazete.gov.tr vb.)
        is_allowed = any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in cls.ALLOWED_DOMAINS
        )

        if not is_allowed:
            return (
                False,
                f"Erişim reddedildi: '{hostname}' izinli resmî alan adları listesinde ({', '.join(cls.ALLOWED_DOMAINS)}) yer almıyor.",
            )

        return True, "Geçerli ve izinli resmî kaynak URL'si."


SourceRegistry = URLAllowlistRegistry
