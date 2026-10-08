import json
from unittest.mock import MagicMock, patch

import pytest
from tarim_destek_rag.models.source import AuthorityEnum, ContentTypeEnum, SourceDefinition
from tarim_destek_rag.scraper.client import (
    InvalidMimeTypeError,
    ScraperClient,
    SnapshotWriter,
)
from tarim_destek_rag.scraper.orchestrator import ScraperOrchestrator
from tarim_destek_rag.scraper.registry import SourceRegistry


def test_snapshot_writer(tmp_path):
    """SnapshotWriter dosya ve metadata.json yazım testi."""
    writer = SnapshotWriter(base_path=str(tmp_path))
    src = SourceDefinition(
        id="SRC-HTML",
        url="https://tarimorman.gov.tr/mevzuat",
        authority=AuthorityEnum.MINISTRY,
        title="Bakanlık Mevzuatı",
        content_type=ContentTypeEnum.HTML,
    )
    fake_content = b"<html><body>2026 Destekleme Karari</body></html>"
    metadata = {"status_code": 200, "url": "https://tarimorman.gov.tr/mevzuat"}

    snap_dir = writer.write_snapshot(src, fake_content, metadata, timestamp_str="20260101T000000Z")
    assert snap_dir.exists()
    assert (snap_dir / "content.html").read_bytes() == fake_content
    meta_saved = json.loads((snap_dir / "metadata.json").read_text(encoding="utf-8"))
    assert meta_saved["status_code"] == 200


@patch("httpx.Client.get")
def test_scraper_mocked_html_success(mock_get):
    """HTML kaynağının HTTP mock ile başarılı çekilmesi."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<html><h1>Bitkisel Uretim</h1></html>"
    mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
    mock_get.return_value = mock_resp

    client = ScraperClient(rate_limit_seconds=0.01)
    src = SourceDefinition(
        id="MOCK-HTML",
        url="https://tarimorman.gov.tr/test",
        authority=AuthorityEnum.MINISTRY,
        title="Test",
        content_type=ContentTypeEnum.HTML,
    )
    content, meta = client.fetch(src)
    assert b"Bitkisel Uretim" in content
    assert meta["status_code"] == 200
    assert "text/html" in meta["content_type"]


@patch("httpx.Client.get")
def test_scraper_mocked_pdf_success(mock_get):
    """PDF kaynağının HTTP mock ile başarılı çekilmesi."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"%PDF-1.4 test binary pdf"
    mock_resp.headers = {"content-type": "application/pdf"}
    mock_get.return_value = mock_resp

    client = ScraperClient(rate_limit_seconds=0.01)
    src = SourceDefinition(
        id="MOCK-PDF",
        url="https://resmigazete.gov.tr/karar.pdf",
        authority=AuthorityEnum.OFFICIAL_GAZETTE,
        title="Karar PDF",
        content_type=ContentTypeEnum.PDF,
    )
    content, meta = client.fetch(src)
    assert content.startswith(b"%PDF")
    assert meta["status_code"] == 200


@patch("httpx.Client.get")
def test_invalid_mime_type_detected(mock_get):
    """PDF beklenen kaynakta HTML dönülmesi halinde InvalidMimeTypeError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<html>Error 404 page</html>"
    mock_resp.headers = {"content-type": "text/html"}
    mock_get.return_value = mock_resp

    client = ScraperClient(rate_limit_seconds=0.01)
    src = SourceDefinition(
        id="MOCK-PDF-FAIL",
        url="https://resmigazete.gov.tr/karar",  # .pdf ile bitmiyor
        authority=AuthorityEnum.OFFICIAL_GAZETTE,
        title="Karar",
        content_type=ContentTypeEnum.PDF,
    )
    with pytest.raises(InvalidMimeTypeError):
        client.fetch(src)


def test_scraper_orchestrator(tmp_path):
    """Orchestrator'ın mock client ile çoklu kaynak kazıması."""
    reg = SourceRegistry()
    src1 = SourceDefinition(
        id="SRC-1",
        url="https://tarimorman.gov.tr/1",
        authority=AuthorityEnum.MINISTRY,
        title="Kaynak 1",
    )
    src2 = SourceDefinition(
        id="SRC-2",
        url="https://tarimorman.gov.tr/2",
        authority=AuthorityEnum.MINISTRY,
        title="Kaynak 2",
    )
    reg.register(src1)
    reg.register(src2)

    mock_client = MagicMock()
    mock_client.fetch.return_value = (b"mock content", {"status_code": 200})

    writer = SnapshotWriter(base_path=str(tmp_path))
    orchestrator = ScraperOrchestrator(registry=reg, client=mock_client, writer=writer)

    results = orchestrator.scrape_all_active()
    assert len(results) == 2
    assert all(r.success for r in results)
    assert (tmp_path / "SRC-1").exists()
    assert (tmp_path / "SRC-2").exists()
