from tarim_destek_rag.change_detector.comparator import (
    ChangeDetector,
    ChangeStatusEnum,
)
from tarim_destek_rag.change_detector.hasher import (
    canonicalize_html,
    compute_content_hash,
)
from tarim_destek_rag.models.source import AuthorityEnum, ContentTypeEnum, SourceDefinition


def test_canonical_html_equivalent():
    """Boşluk ve script farklarına rağmen aynı kanonik metin üretimi."""
    html_1 = (
        b"<html><head><script>alert(1);</script></head><body><h1>Tarim  Destegi</h1></body></html>"
    )
    html_2 = b"<html><body><h1> Tarim Destegi </h1></body></html>"

    can_1 = canonicalize_html(html_1)
    can_2 = canonicalize_html(html_2)
    assert can_1 == can_2 == "Tarim Destegi"

    hash_1 = compute_content_hash(html_1, is_html=True)
    hash_2 = compute_content_hash(html_2, is_html=True)
    assert hash_1 == hash_2


def test_deterministic_hash():
    """Deterministik SHA-256 çıktısı testi."""
    raw = b"2026 Destekleme Kararnamesi Metni"
    h1 = compute_content_hash(raw)
    h2 = compute_content_hash(raw)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex string


def test_change_detector_lifecycle():
    """NEW -> UNCHANGED -> UPDATED döngüsü ve supersession adayı testi."""
    detector = ChangeDetector()
    src = SourceDefinition(
        id="RG-BITKISEL",
        url="https://resmigazete.gov.tr/karar",
        authority=AuthorityEnum.OFFICIAL_GAZETTE,
        title="2026 Kararı",
        content_type=ContentTypeEnum.HTML,
    )

    content_v1 = b"<html><body>Findik destegi 170 TL</body></html>"
    content_v2 = b"<html><body>Findik destegi 170 TL</body></html>"
    content_v3 = b"<html><body>Findik destegi 200 TL (Guncellendi)</body></html>"

    # 1. İlk keşif: NEW
    event_1 = detector.evaluate(src, content_v1)
    assert event_1.status == ChangeStatusEnum.NEW
    assert event_1.old_hash is None
    assert event_1.new_hash is not None
    assert not event_1.superseded_candidate

    # 2. Aynı içerik: UNCHANGED
    event_2 = detector.evaluate(src, content_v2)
    assert event_2.status == ChangeStatusEnum.UNCHANGED
    assert event_2.old_hash == event_1.new_hash
    assert not event_2.superseded_candidate

    # 3. Güncelleme: UPDATED ve superseded adayı
    event_3 = detector.evaluate(src, content_v3)
    assert event_3.status == ChangeStatusEnum.UPDATED
    assert event_3.old_hash == event_1.new_hash
    assert event_3.new_hash != event_1.new_hash
    assert event_3.superseded_candidate

    # Tarihçe doğrulaması
    history = detector.get_events("RG-BITKISEL")
    assert len(history) == 3
