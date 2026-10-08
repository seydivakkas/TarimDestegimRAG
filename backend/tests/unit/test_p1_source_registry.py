import pytest
from pydantic import ValidationError
from tarim_destek_rag.models.source import AuthorityEnum, ContentTypeEnum, SourceDefinition
from tarim_destek_rag.scraper.registry import (
    DuplicateSourceIdError,
    SourceNotFoundError,
    SourceRegistry,
)


def test_source_schema_validation():
    """Geçerli bir kaynak tanımının şema ve priority otomatik hesabı."""
    src = SourceDefinition(
        id="TEST-01",
        url="https://resmigazete.gov.tr/test",
        authority=AuthorityEnum.OFFICIAL_GAZETTE,
        title="Test Resmî Gazete Kaynağı",
        content_type=ContentTypeEnum.PDF,
        active=True,
    )
    assert src.id == "TEST-01"
    assert src.priority == 0  # Resmî Gazete P0 olmalı


def test_invalid_url_rejected():
    """Geçersiz URL formatının reddedilmesi."""
    with pytest.raises(ValidationError):
        SourceDefinition(
            id="TEST-INVALID",
            url="not_a_valid_url",
            authority=AuthorityEnum.MINISTRY,
            title="Geçersiz URL",
        )


def test_duplicate_source_rejection():
    """Mükerrer ID ile kayıt girişiminde DuplicateSourceIdError fırlatılması."""
    reg = SourceRegistry()
    src1 = SourceDefinition(
        id="DUP-ID",
        url="https://tarimorman.gov.tr/kaynak1",
        authority=AuthorityEnum.MINISTRY,
        title="Kaynak 1",
    )
    src2 = SourceDefinition(
        id="DUP-ID",
        url="https://tarimorman.gov.tr/kaynak2",
        authority=AuthorityEnum.MINISTRY,
        title="Kaynak 2",
    )
    reg.register(src1)
    with pytest.raises(DuplicateSourceIdError):
        reg.register(src2)


def test_source_not_found():
    """Kayıtlı olmayan kaynak istendiğinde SourceNotFoundError fırlatılması."""
    reg = SourceRegistry()
    with pytest.raises(SourceNotFoundError):
        reg.get_source("NON_EXISTING")


def test_disabled_source_filtering():
    """Pasif kaynakların list_active_sources() listesinde yer almaması."""
    reg = SourceRegistry()
    src_active = SourceDefinition(
        id="ACTIVE-01",
        url="https://tarimorman.gov.tr/active",
        authority=AuthorityEnum.MINISTRY,
        title="Aktif Kaynak",
        active=True,
    )
    src_inactive = SourceDefinition(
        id="INACTIVE-01",
        url="https://tarimorman.gov.tr/inactive",
        authority=AuthorityEnum.MINISTRY,
        title="Pasif Kaynak",
        active=False,
    )
    reg.register(src_active)
    reg.register(src_inactive)

    active_list = reg.list_active_sources()
    assert len(active_list) == 1
    assert active_list[0].id == "ACTIVE-01"


def test_priority_order():
    """P0 (Resmî Gazete) > P1 (Bakanlık) > P2 (Genel Md.) > P3 (İl Md.) sıralaması."""
    reg = SourceRegistry()
    s_p3 = SourceDefinition(
        id="P3-SRC",
        url="https://konya.tarimorman.gov.tr",
        authority=AuthorityEnum.PROVINCIAL_DIRECTORATE,
        title="İl Müdürlüğü",
    )
    s_p0 = SourceDefinition(
        id="P0-SRC",
        url="https://resmigazete.gov.tr",
        authority=AuthorityEnum.OFFICIAL_GAZETTE,
        title="Resmî Gazete",
    )
    s_p1 = SourceDefinition(
        id="P1-SRC",
        url="https://tarimorman.gov.tr",
        authority=AuthorityEnum.MINISTRY,
        title="Bakanlık",
    )
    reg.register(s_p3)
    reg.register(s_p0)
    reg.register(s_p1)

    sorted_active = reg.list_active_sources()
    ids = [s.id for s in sorted_active]
    assert ids == ["P0-SRC", "P1-SRC", "P3-SRC"]


def test_load_from_yaml():
    """configs/sources.yaml dosyasından kaynakların eksiksiz yüklenmesi."""
    reg = SourceRegistry.load_from_yaml("configs/sources.yaml")
    sources = reg.list_all()
    assert len(sources) >= 5
    assert reg.get_source("RG-2026-BITKISEL").authority == AuthorityEnum.OFFICIAL_GAZETTE
