"""P0: gerçek PDF/HTML sayfa kanıtı, hash bütünlüğü ve ret senaryoları."""
import io

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from tarim_destek_rag.citations.evidence import (
    EvidenceError, EvidenceStore, extract_document_pages, require_official_https,
)
from tarim_destek_rag.citations.verifier import CitationVerifier
from tarim_destek_rag.explainer.template_explainer import CitationDetail
from tarim_destek_rag.models.source import AuthorityEnum, ContentTypeEnum, SourceDefinition
from tarim_destek_rag.scraper.registry import SourceRegistry


def make_source(url="https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi", fmt="HTML"):
    return SourceDefinition(
        id="P0-OFFICIAL", title="2026 katsayı düzenlemesi", url=url,
        authority=AuthorityEnum.MINISTRY, content_type=ContentTypeEnum(fmt),
    )


def make_pdf(text: str) -> bytes:
    """PyPDF ile dış kütüphane ve internet gerektirmeden text layer içeren PDF."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): writer._add_object(font),
        })
    })
    stream = DecodedStreamObject()
    stream.set_data(("BT /F1 12 Tf 50 700 Td (" + text + ") Tj ET").encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def register(source):
    registry = SourceRegistry()
    registry.register(source)
    return registry


def test_ministry_html_passage_verified_only_when_exact_section_matches(tmp_path):
    source = make_source()
    html = b"""<!doctype html><html><body><h1>DESTEK TUTARLARI ARTIRILDI</h1>
    <article><p>2026 uretim yili icin destek katsayi degeri 367 TL olarak guncellendi.</p></article>
    </body></html>"""
    store = EvidenceStore(tmp_path)
    snapshot = store.index_bytes(source, html)
    store.save_snapshot(snapshot, html)
    verifier = CitationVerifier(register(source), EvidenceStore(tmp_path))
    good = CitationDetail(source_id=source.id, title="Bakanlık", year=2026,
                          section="DESTEK TUTARLARI ARTIRILDI",
                          snippet="destek katsayi degeri 367 TL olarak guncellendi.",
                          url=str(source.url))
    result = verifier.verify(good)
    assert result.is_valid and result.status == "VERIFIED"
    assert result.page_number == 1 and result.document_sha256 == snapshot.sha256
    assert verifier.verify(good.model_copy(update={"snippet": "katsayi degeri 999 TL"})).status == "PASSAGE_NOT_FOUND"
    assert verifier.verify(good.model_copy(update={"section": "MADDE 99"})).status == "PASSAGE_NOT_FOUND"
    assert verifier.verify(good.model_copy(update={"url": "https://example.com/fake"})).status == "SOURCE_URL_MISMATCH"


def test_real_pdf_text_layer_and_page_anchor(tmp_path):
    source = make_source("https://www.tarimorman.gov.tr/BUGEM/destek.pdf", fmt="PDF")
    content = make_pdf("MADDE 1 resmi belgede katsayi 367 TL olarak guncellendi")
    store = EvidenceStore(tmp_path)
    snapshot = store.index_bytes(source, content)
    store.save_snapshot(snapshot, content)
    verifier = CitationVerifier(register(source), EvidenceStore(tmp_path))
    citation = CitationDetail(source_id=source.id, title="PDF", year=2026,
                              section="MADDE 1", snippet="katsayi 367 TL olarak guncellendi",
                              url=str(source.url) + "#page=1")
    good = verifier.verify(citation)
    assert good.is_valid and good.page_number == 1
    wrong = verifier.verify(citation.model_copy(update={"url": str(source.url) + "#page=2"}))
    assert wrong.status == "PAGE_MISMATCH"


def test_snapshot_hash_tamper_fails_closed(tmp_path):
    source = make_source()
    payload = b"<html><body>resmi yayin metni</body></html>"
    store = EvidenceStore(tmp_path)
    snapshot = store.index_bytes(source, payload)
    store.save_snapshot(snapshot, payload)
    (tmp_path / source.id / f"{snapshot.sha256}.html").write_bytes(b"<html>degistirildi</html>")
    assert EvidenceStore(tmp_path).load_snapshot(source) is None


@pytest.mark.parametrize("url", [
    "http://www.tarimorman.gov.tr/Haber/test",
    "https://tarimorman.gov.tr.evil.test/p",
    "https://127.0.0.1/test",
    "https://www.tarimorman.gov.tr:444/test",
    "https://www.tarimorman.gov.tr@evil.test/test",
])
def test_unofficial_or_insecure_url_rejected(url):
    with pytest.raises(EvidenceError):
        require_official_https(url)


def test_empty_document_and_pdf_without_text_rejected():
    with pytest.raises(EvidenceError):
        extract_document_pages(b"", ContentTypeEnum.HTML)
    blank = PdfWriter()
    blank.add_blank_page(width=200, height=200)
    target = io.BytesIO()
    blank.write(target)
    with pytest.raises(EvidenceError):
        extract_document_pages(target.getvalue(), ContentTypeEnum.PDF)


def test_unloaded_snapshot_does_not_pass(tmp_path):
    source = make_source()
    verifier = CitationVerifier(register(source), EvidenceStore(tmp_path))
    citation = CitationDetail(source_id=source.id, title="Resmi", year=2026,
                              section="2026", snippet="katsayi 367 TL olarak guncellendi",
                              url=str(source.url))
    assert verifier.verify(citation).status == "EVIDENCE_NOT_INDEXED"
