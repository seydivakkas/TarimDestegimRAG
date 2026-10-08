"""Kaynak kayıt, hash ve belge-pasaj kanıt doğrulayıcısı (fail closed)."""

import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, Field

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

        # Source registration or a user-provided text snippet never proves
        # the legal statement. Require the original officially downloaded
        # PDF/HTML with pinned SHA and exact passage before VERIFIED.
        proof = self.verify(citation)
        if not proof.is_valid:
            return ClaimVerificationResult(
                is_valid=False,
                status="EVIDENCE_NOT_INDEXED" if proof.status == "EVIDENCE_NOT_INDEXED"
                else "UNVERIFIED_SOURCE",
                message="Original source bytes/passage not independently verified",
                claim_supported=False, span_matched=False,
                version_valid=proof.year_valid, confidence_score=0.0,
            )

        # 6. Only independently proven source/passage can be VERIFIED.
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
