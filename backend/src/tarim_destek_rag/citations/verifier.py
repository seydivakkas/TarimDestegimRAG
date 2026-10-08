"""Kaynak kayıt, hash ve belge-pasaj kanıt doğrulayıcısı (fail closed)."""

from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel

from tarim_destek_rag.citations.evidence import EvidenceStore, canonical_url
from tarim_destek_rag.explainer.template_explainer import CitationDetail
from tarim_destek_rag.scraper.registry import SourceRegistry, source_registry


class VerificationResult(BaseModel):
    is_valid: bool
    source_exists: bool
    source_active: bool
    year_valid: bool
    status: str
    message: str
    document_sha256: str | None = None
    page_number: int | None = None


class CitationVerifier:
    """Atıf, ancak izinli URL'den alınmış gerçek belgede pasaj eşleşirse geçerlidir."""

    def __init__(
        self,
        registry: SourceRegistry | None = None,
        evidence_store: EvidenceStore | None = None,
    ) -> None:
        self.registry = registry if registry is not None else source_registry
        self.evidence_store = evidence_store if evidence_store is not None else EvidenceStore()

    def verify(self, citation: CitationDetail) -> VerificationResult:
        def rejected(status: str, msg: str, *, exists=True, active=True, year=True) -> VerificationResult:
            return VerificationResult(
                is_valid=False, source_exists=exists, source_active=active,
                year_valid=year, status=status, message=msg,
            )

        try:
            source = self.registry.get_source(citation.source_id)
        except Exception:
            return rejected(
                "INSUFFICIENT_EVIDENCE", f"Kaynak kayıtlı değil: {citation.source_id}",
                exists=False, active=False, year=False,
            )
        if not source.active:
            return rejected("INACTIVE_SOURCE", f"Kaynak pasif: {citation.source_id}", active=False, year=False)
        if citation.year != 2026:
            return rejected("OUTDATED_YEAR", f"Atıf hedef yılı 2026 değil: {citation.year}", year=False)

        if not citation.url or canonical_url(citation.url) != canonical_url(str(source.url)):
            return rejected("SOURCE_URL_MISMATCH", "Atıf URL'si kayıtlı resmî kaynak URL'siyle uyuşmuyor.")

        snapshot = self.evidence_store.get(source.id)
        if snapshot is None:
            snapshot = self.evidence_store.load_snapshot(source)
        if snapshot is None:
            return rejected("EVIDENCE_NOT_INDEXED", "Gerçek kaynak belgesi henüz indirilemedi veya hash doğrulanamadı.")

        ok, page = self.evidence_store.match(source, snippet=citation.snippet, section=citation.section)
        if not ok or page is None:
            return rejected("PASSAGE_NOT_FOUND", "Atıf pasajı ve belirtilen bölüm aynı belge sayfasında eşleşmedi.")

        fragment = urlsplit(citation.url).fragment
        if fragment:
            values = parse_qs(fragment).get("page")
            if values:
                try:
                    if len(values) != 1 or int(values[0]) != page:
                        return rejected("PAGE_MISMATCH", "Atıfta verilen PDF sayfası eşleşmiyor.")
                except ValueError:
                    return rejected("PAGE_MISMATCH", "Geçersiz sayfa numarası.")

        return VerificationResult(
            is_valid=True, source_exists=True, source_active=True, year_valid=True,
            status="VERIFIED",
            message="Kaynağın hash'i doğrulandı; ilgili bölüm ve pasaj belgede bulundu.",
            document_sha256=snapshot.sha256, page_number=page,
        )


citation_verifier = CitationVerifier()
