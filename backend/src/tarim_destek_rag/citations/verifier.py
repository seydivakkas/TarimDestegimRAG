"""Mevzuat Atıf ve İddia Doğrulama Motoru (Citation & Claim Verifier).

Master Plan & Issue #5 Uyumlu:
- İddia-Paragraf (Claim-to-Span) ve Belge Sürümü Eşleştirme.
- Atıfsız, Eski Sürümlü, ve Semantik Olarak Yanlış Eşleşen İddiaları Ayıklama.
- Ayrık Metrikler: Citation Precision, Citation Recall, Unsupported Claim Rate,
  Legal Freshness ve Refusal Accuracy.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from tarim_destek_rag.explainer.template_explainer import CitationDetail
from tarim_destek_rag.scraper.registry import SourceRegistry, source_registry


class VerificationResult(BaseModel):
    """Tekil atıf doğrulama sonucu."""

    is_valid: bool
    source_exists: bool
    source_active: bool
    year_valid: bool
    status: str
    message: str


class ClaimVerificationResult(BaseModel):
    """İddia-paragraf ve mevzuat sürümü doğrulama sonucu (Issue #5)."""

    is_valid: bool
    status: str  # VERIFIED, NO_CITATION, OUTDATED_VERSION, UNSUPPORTED_CLAIM, SPAN_MISMATCH, INACTIVE_SOURCE, EMPTY_OR_SHORT_SNIPPET
    message: str
    claim_supported: bool
    span_matched: bool
    version_valid: bool
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class CitationMetricsResult(BaseModel):
    """Atıf ve RAG güvenilirlik metrikleri özeti."""

    total_claims: int
    citation_precision: float
    citation_recall: float
    unsupported_claim_rate: float
    legal_freshness: float
    refusal_accuracy: float


class CitationVerifier:
    """Mevzuat iddialarının, gösterilen kaynakların ve metin aralıklarının geçerliliğini denetleyen guard."""

    def __init__(self, registry: SourceRegistry | None = None) -> None:
        if registry:
            self.registry = registry
        else:
            self.registry = source_registry
            if not self.registry.list_all():
                try:
                    from pathlib import Path
                    cfg_path = Path("configs/sources.yaml")
                    if cfg_path.exists():
                        loaded = SourceRegistry.load_from_yaml(cfg_path)
                        for s in loaded.list_all():
                            if s.id not in self.registry._sources:
                                self.registry.register(s)
                except Exception:
                    pass

    def verify(self, citation: CitationDetail) -> VerificationResult:
        """Tek bir atfın kaynak ve yıl geçerlilik zincirini denetler (Geriye dönük uyumluluk)."""
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

        snippet_clean = citation.snippet.strip() if getattr(citation, "snippet", None) else ""
        if not snippet_clean or len(snippet_clean) < 10:
            return VerificationResult(
                is_valid=False,
                source_exists=True,
                source_active=True,
                year_valid=True,
                status="EMPTY_OR_SHORT_SNIPPET",
                message="Atıf metni (snippet) boş veya geçersiz uzunlukta (<10 karakter).",
            )

        section_clean = citation.section.strip() if getattr(citation, "section", None) else ""
        if not section_clean:
            return VerificationResult(
                is_valid=False,
                source_exists=True,
                source_active=True,
                year_valid=True,
                status="MISSING_SECTION",
                message="Atıf yapılan mevzuat maddesi/bölümü belirtilmemiş.",
            )

        return VerificationResult(
            is_valid=True,
            source_exists=True,
            source_active=True,
            year_valid=True,
            status="VERIFIED",
            message="Kaynak resmî, aktif ve 2026 yılı için doğrulanmış mevzuat maddesidir.",
        )

    def verify_claim(
        self,
        claim_text: str,
        citation: CitationDetail | None,
        document_text: str | None = None,
    ) -> ClaimVerificationResult:
        """Bir iddia cümlesini ilgili atıf ve kaynak metin aralığı (claim-to-span) bazında inceler."""
        # 1. Negatif Durum: Atıfsız İddia (NO_CITATION)
        if citation is None:
            return ClaimVerificationResult(
                is_valid=False,
                status="NO_CITATION",
                message="İddia için hiçbir resmî mevzuat atfı belirtilmedi.",
                claim_supported=False,
                span_matched=False,
                version_valid=False,
                confidence_score=0.0,
            )

        # 2. Kaynak Varlık ve Aktiflik Kontrolü
        try:
            source = self.registry.get_source(citation.source_id)
        except Exception:
            return ClaimVerificationResult(
                is_valid=False,
                status="INSUFFICIENT_EVIDENCE",
                message=f"Atıf yapılan kaynak sistemde kayıtlı değil: {citation.source_id}",
                claim_supported=False,
                span_matched=False,
                version_valid=False,
                confidence_score=0.0,
            )

        if not source.active:
            return ClaimVerificationResult(
                is_valid=False,
                status="INACTIVE_SOURCE",
                message=f"Atıf kaynağı aktif değil: {citation.source_id}",
                claim_supported=False,
                span_matched=False,
                version_valid=False,
                confidence_score=0.0,
            )

        # 3. Negatif Durum: Eski Sürümlü / Mülga Mevzuat (OUTDATED_VERSION)
        if citation.year != 2026:
            return ClaimVerificationResult(
                is_valid=False,
                status="OUTDATED_VERSION",
                message=f"Atıf yapılan mevzuat yılı 2026 değil ({citation.year}); mülga mevzuat kullanılamaz.",
                claim_supported=False,
                span_matched=False,
                version_valid=False,
                confidence_score=0.0,
            )

        snippet = (citation.snippet or "").strip()
        if len(snippet) < 10:
            return ClaimVerificationResult(
                is_valid=False,
                status="EMPTY_OR_SHORT_SNIPPET",
                message="Atıf parçası (snippet) boş veya yetersiz uzunlukta.",
                claim_supported=False,
                span_matched=False,
                version_valid=True,
                confidence_score=0.0,
            )

        # 4. Negatif Durum: Span Uyuşmazlığı (SPAN_MISMATCH)
        # Eğer tam doküman metni verildiyse, alıntılanan snippet'in o belgede gerçekten var olduğu teyit edilmelidir.
        if document_text is not None:
            norm_doc = " ".join(document_text.lower().split())
            norm_snip = " ".join(snippet.lower().split())
            if norm_snip not in norm_doc:
                return ClaimVerificationResult(
                    is_valid=False,
                    status="SPAN_MISMATCH",
                    message="Atıf gösterilen snippet kaynak mevzuat dokümanında bulunamadı.",
                    claim_supported=False,
                    span_matched=False,
                    version_valid=True,
                    confidence_score=0.2,
                )

        # 5. Negatif Durum: Semantik Olarak Yanlış / Desteksiz Eşleşme (UNSUPPORTED_CLAIM)
        claim_norm = claim_text.lower()
        snippet_norm = snippet.lower()

        # Rakam ve tutar kontrolü: İddiadaki sayısal değerler snippet'te yer alıyor mu?
        claim_numbers = re.findall(r"\b\d+(?:[.,]\d+)?\b", claim_norm)
        snippet_numbers = re.findall(r"\b\d+(?:[.,]\d+)?\b", snippet_norm)

        for num in claim_numbers:
            # Yıl (2026) hariç sayısal tutarların snippet içinde bulunması gerekir
            if num not in {"2026", "2025", "2024", "1", "2", "3", "4", "5", "6", "7", "8", "9"} and num not in snippet_numbers:
                return ClaimVerificationResult(
                    is_valid=False,
                    status="UNSUPPORTED_CLAIM",
                    message=f"İddiadaki sayısal tutar ({num}) atıf gösterilen mevzuat metninde yer almıyor veya çelişiyor.",
                    claim_supported=False,
                    span_matched=True,
                    version_valid=True,
                    confidence_score=0.1,
                )

        # Temel ürün adı çelişkisi kontrolü (örn. iddia 'fındık' iken snippet yalnızca 'buğday'dan bahsediyorsa)
        crops = ["buğday", "arpa", "pamuk", "ayçiçeği", "fındık", "mısır", "mercimek", "nohut", "soya", "kayısı"]
        claim_crops = [c for c in crops if c in claim_norm]
        snippet_crops = [c for c in crops if c in snippet_norm]

        if claim_crops and snippet_crops:
            if not any(c in snippet_crops for c in claim_crops):
                return ClaimVerificationResult(
                    is_valid=False,
                    status="UNSUPPORTED_CLAIM",
                    message=f"İddiadaki ürün ({', '.join(claim_crops)}) atıf metnindeki kapsamla ({', '.join(snippet_crops)}) örtüşmüyor.",
                    claim_supported=False,
                    span_matched=True,
                    version_valid=True,
                    confidence_score=0.1,
                )

        # 6. Tüm koşullar sağlandı: VERIFIED
        return ClaimVerificationResult(
            is_valid=True,
            status="VERIFIED",
            message="İddia, resmî mevzuat maddesi ve doğrulanmış kanıt parçasıyla tam uyumludur.",
            claim_supported=True,
            span_matched=True,
            version_valid=True,
            confidence_score=1.0,
        )


class CitationMetricsCalculator:
    """Atıf güvenilirliği, unsupported-claim rate ve refusal accuracy hesaplayıcısı."""

    @classmethod
    def calculate_metrics(
        cls,
        eval_cases: list[dict[str, Any]],
        verifier: CitationVerifier | None = None,
    ) -> CitationMetricsResult:
        """Değerlendirme vakaları üzerinden ayrıntılı kalite metriklerini hesaplar."""
        v = verifier or citation_verifier
        total_claims = len(eval_cases)
        if total_claims == 0:
            return CitationMetricsResult(
                total_claims=0,
                citation_precision=0.0,
                citation_recall=0.0,
                unsupported_claim_rate=0.0,
                legal_freshness=0.0,
                refusal_accuracy=0.0,
            )

        supported_citations = 0
        total_citations_returned = 0
        ground_truth_supported = 0
        unsupported_claims = 0
        fresh_citations = 0
        correct_refusals = 0
        total_unsupportable = 0

        for case in eval_cases:
            claim = case.get("claim", "")
            cit = case.get("citation")
            doc = case.get("document_text")
            is_unsupportable = case.get("is_unsupportable", False)

            if is_unsupportable:
                total_unsupportable += 1

            if cit is not None:
                total_citations_returned += 1
                if cit.year == 2026:
                    fresh_citations += 1

            result = v.verify_claim(claim, cit, doc)

            if result.is_valid and result.claim_supported:
                supported_citations += 1
                if not is_unsupportable:
                    ground_truth_supported += 1
            else:
                unsupported_claims += 1
                if is_unsupportable:
                    correct_refusals += 1

        precision = (
            supported_citations / total_citations_returned
            if total_citations_returned > 0
            else 0.0
        )
        expected_supported_count = total_claims - total_unsupportable
        recall = (
            ground_truth_supported / expected_supported_count
            if expected_supported_count > 0
            else 1.0
        )
        unsupported_rate = unsupported_claims / total_claims
        freshness = (
            fresh_citations / total_citations_returned
            if total_citations_returned > 0
            else 0.0
        )
        refusal_acc = (
            correct_refusals / total_unsupportable
            if total_unsupportable > 0
            else 1.0
        )

        return CitationMetricsResult(
            total_claims=total_claims,
            citation_precision=round(precision, 4),
            citation_recall=round(recall, 4),
            unsupported_claim_rate=round(unsupported_rate, 4),
            legal_freshness=round(freshness, 4),
            refusal_accuracy=round(refusal_acc, 4),
        )


citation_verifier = CitationVerifier()
