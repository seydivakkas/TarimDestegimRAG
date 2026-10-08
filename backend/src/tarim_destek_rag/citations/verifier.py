from pydantic import BaseModel

from tarim_destek_rag.explainer.template_explainer import CitationDetail
from tarim_destek_rag.scraper.registry import SourceRegistry, source_registry


class VerificationResult(BaseModel):
    """Atıf doğrulama sonucu."""

    is_valid: bool
    source_exists: bool
    source_active: bool
    year_valid: bool
    status: str
    message: str


class CitationVerifier:
    """Mevzuat iddialarının ve gösterilen kaynakların geçerliliğini denetleyen guard."""

    def __init__(self, registry: SourceRegistry | None = None) -> None:
        self.registry = registry or source_registry

    def verify(self, citation: CitationDetail) -> VerificationResult:
        """Tek bir atfın geçerlilik zincirini denetler."""
        try:
            source = self.registry.get_source(citation.source_id)
        except Exception:
            return VerificationResult(
                is_valid=False,
                source_exists=False,
                source_active=False,
                year_valid=False,
                status="INSUFFICIENT_EVIDENCE",
                message=f"Atıf yapılan kaynak sistemde kayıtlı değil: {citation.source_id}",
            )

        if not source.active:
            return VerificationResult(
                is_valid=False,
                source_exists=True,
                source_active=False,
                year_valid=False,
                status="INACTIVE_SOURCE",
                message=f"Atıf yapılan kaynak pasif duruma alınmış: {citation.source_id}",
            )

        year_valid = citation.year == 2026
        if not year_valid:
            return VerificationResult(
                is_valid=False,
                source_exists=True,
                source_active=True,
                year_valid=False,
                status="OUTDATED_YEAR",
                message=f"Atıf yapılan mevzuat yılı 2026 değil: {citation.year}",
            )

        # Kayıtta bulunması, belgenin doğru maddesini ve alıntısını kanıtlamaz.
        # İçerik hash'i, sürüm ve madde/pasaj eşleşmesi uygulanana kadar
        # iddiayı belge ile doğrulanmış saymıyoruz (fail closed).
        return VerificationResult(
            is_valid=False,
            source_exists=True,
            source_active=True,
            year_valid=True,
            status="INSUFFICIENT_EVIDENCE",
            message=(
                "Kaynak meta verisi eşleşti; fakat belge sürümü, madde ve alıntı "
                "içeriği doğrulanmadığı için resmî kanıt sayılmaz."
            ),
        )


citation_verifier = CitationVerifier()
