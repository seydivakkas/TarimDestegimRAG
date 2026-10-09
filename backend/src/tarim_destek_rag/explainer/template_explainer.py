from pydantic import BaseModel, Field

from tarim_destek_rag.calculator.calculator import CalculationResult
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.retrieval.models import DocumentChunk
from tarim_destek_rag.rules.base import RuleResult


class CitationDetail(BaseModel):
    """Mevzuat kanıt ve atıf ayrıntısı."""

    source_id: str
    title: str
    section: str
    year: int = 2026
    url: str | None = None
    snippet: str
    # The text above is an explanation, NOT a source quotation unless matched.
    verification_status: str = "UNVERIFIED_EXPLANATION"
    highlighted_pdf_url: str | None = None
    document_sha256: str | None = None
    page_number: int | None = None


class ExplanationResult(BaseModel):
    """Kullanıcıya gösterilecek zengin, kaynaklı açıklama kartı."""

    support_id: str
    support_name: str
    status: EligibilityStatusEnum
    status_label_tr: str
    summary_tr: str
    detailed_reason_tr: str
    missing_requirements_tr: list[str] = Field(default_factory=list)
    next_actions_tr: list[str] = Field(default_factory=list)
    citations: list[CitationDetail] = Field(default_factory=list)


SUPPORT_CITATION_DEFAULTS: dict[str, CitationDetail] = {
    "BASIC_SUPPORT_2026": CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 1 - Temel Destek ve ÇKS Zorunluluğu",
        year=2026,
        url="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
        snippet=(
            "2026 katsayı düzenlemesi 367 TL/da; BÜGEM 2. kategoride buğday/arpada temel destek 1,3 × 367 = 477,10 TL/da. Kaynak başlıkları referanstır; içerik/pasaj eşleşmesi bağımsız doğrulanmamıştır."
        ),
    ),
    "PLANNED_PRODUCTION_2026": CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 2 - Tarım Havzaları Planlı Üretim Desteği",
        year=2026,
        url="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
        snippet=(
            "2026 üretim yılında buğday/arpada planlı destek 1,3 × 367 = 477,10 TL/da referansıdır. Havza, ürün ve münavebe şartları ayrıca sağlanmalıdır. Bu açıklama doğrudan mevzuat alıntısı değildir."
        ),
    ),
    "CERTIFIED_SEED_2026": CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 3 - Sertifikalı Tohum Kullanım Desteği",
        year=2026,
        url="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
        snippet=(
            "2026 buğday/arpada sertifikalı tohum katsayısı 0,56 × 367 = 205,52 TL/da'dır. Sertifika ve kayıt belgeleri ilgili tebliğ koşullarına göre kontrol edilmelidir. Doğrudan mevzuat alıntısı değildir."
        ),
    ),
    "CERTIFIED_SAPLING_2026": CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 6 - Sertifikalı Fidan ve Kapama Bahçe Şartı",
        year=2026,
        url="https://www.tarimorman.gov.tr/BUGEM/Menu/16/Sertifikali-Fidan-Kullanim-Destegi",
        snippet=(
            "BÜGEM 2026 cetvelinde sertifikalı meyve fidanı katsayısı 5 × 367 = 1.835,00 TL/da referansı verir. Gerçek uygunluk bitki türü, belge ve bahçe kurulum şartlarına bağlıdır."
        ),
    ),
    "WATER_RESTRICTION_2026": CitationDetail(
        source_id="TOB-SU-KISITI-2026",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 4 - Yeraltı Su Kısıtı Olan Havzalar Desteği",
        year=2026,
        url="https://www.tarimorman.gov.tr/BUGEM/Menu/17/Yeralti-Sularinin-Yetersiz-Oldugu-Havzalar",
        snippet=(
            "2026 su kısıtı 1. kategori ilave destek katsayısı 0,8 × 367 = 293,60 TL/da. Yalnız tanımlı su kısıtı havzasında sulu tarım arazisi ve uygun ürün koşulları sağlanırsa değerlendirilir."
        ),
    ),
}


class TemplateExplainer:
    """Kural motoru çıktılarını Türkçe mevzuat diliyle açıklayan şablon motoru."""

    @staticmethod
    def explain(
        rule_res: RuleResult,
        calc_res: CalculationResult | None = None,
        retrieved_chunks: list[DocumentChunk] | None = None,
    ) -> ExplanationResult:
        """Kural kararı ve hesaplamaya göre insan dilinde şeffaf gerekçe üretir."""
        citations: list[CitationDetail] = []

        # Import lazily to avoid citations.verifier -> explainer circular imports.
        from tarim_destek_rag.citations.exact_index import lookup_exact_pdf_citation

        # 1. A source-bound quote supersedes descriptive defaults ONLY after
        # independent page/byte/coordinate checks against the original PDF.
        # Otherwise the defaults remain clearly labelled as explanations.
        proof = lookup_exact_pdf_citation(rule_res.support_id)
        primary_citation = SUPPORT_CITATION_DEFAULTS.get(rule_res.support_id)
        if proof:
            citations.append(CitationDetail(
                source_id=proof["source_id"],
                title=proof["title"],
                section=proof["section"],
                year=proof["year"],
                url=f'{proof["source_url"]}#page={proof["page_number"]}',
                snippet=proof["exact_quote"],
                verification_status=proof["verification_status"],
                highlighted_pdf_url=proof["highlighted_pdf_url"],
                document_sha256=proof["source_sha256"],
                page_number=proof["page_number"],
            ))
        elif primary_citation:
            citations.append(primary_citation)

        # 2. Vektör / Semantik arama ile eşleşen ek mevzuat parçalarını ekle
        if retrieved_chunks:
            for c in retrieved_chunks:
                # Birincil atıf ile mükerrer olmasını engelle
                if primary_citation and c.section == primary_citation.section:
                    continue
                snip = c.text[:220] + "..." if len(c.text) > 220 else c.text
                c_url = c.url or (primary_citation.url if primary_citation else "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf")
                citations.append(
                    CitationDetail(
                        source_id=c.source_id,
                        title=c.title,
                        section=c.section,
                        year=c.year,
                        url=c_url,
                        snippet=snip,
                    )
                )

        if not citations:
            citations.append(
                CitationDetail(
                    source_id="RG-2026-BITKISEL",
                    title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
                    section="Madde 3 & Ek Tablo",
                    year=2026,
                    url="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf",
                    snippet="2026 yılı bitkisel üretim destekleme birim tutarları ve esasları.",
                )
            )


        missing_tr: list[str] = []
        next_actions: list[str] = []

        if "cks_status" in rule_res.missing_fields:
            missing_tr.append("Çiftçi Kayıt Sistemi (ÇKS) 2026 üretim yılı aktif kayıt durumu")
            next_actions.append(
                "İl/İlçe Tarım Müdürlüğü veya e-Devlet üzerinden ÇKS kaydınızı yenileyiniz."
            )

        if "seed_certificate_available" in rule_res.missing_fields:
            missing_tr.append(
                "Yetkili tohumluk bayisinden alınmış sertifikalı tohum fatura ve belgesi"
            )
            next_actions.append("Tohum sertifikanızı başvuru dosyasına ekleyiniz.")

        if "sapling_certificate_available" in rule_res.missing_fields:
            missing_tr.append("Sertifikalı/standart fidan alım belgesi ve etiketleri")
            next_actions.append("Fidan sertifikalarını ilçe müdürlüğüne ibraz ediniz.")

        # Durum Bazlı Şablonlar
        if rule_res.status == EligibilityStatusEnum.ELIGIBLE:
            status_label = "Uygun görünüyor"
            if calc_res and calc_res.estimated_amount:
                amt_str = f"{calc_res.estimated_amount:,.2f} TL"
            else:
                amt_str = "Belirleniyor"
            summary = (
                f"{rule_res.support_name} için tüm mevzuat şartlarını sağlıyorsunuz. "
                f"Tahmini ön değerlendirme tutarınız: {amt_str}."
            )
            passed_items = "\n".join([f"• {chk}" for chk in rule_res.passed_checks])
            reasons = f"Değerlendirme Başarılı:\n{passed_items}"
            next_actions.append(
                "Belirtilen başvuru takvimi içinde ilçe tarım müdürlüğüne başvurunuzu iletiniz."
            )

        elif rule_res.status == EligibilityStatusEnum.REVIEW:
            status_label = "Ek kontrol gerekiyor"
            summary = (
                f"{rule_res.support_name} değerlendirmesi için bazı zorunlu bilgiler eksiktir. "
                "Eksik bilgileri tamamlayarak tekrar değerlendiriniz."
            )
            missing_items = "\n".join([f"• {m}" for m in missing_tr])
            reasons = f"Eksik / Doğrulama Gerektiren Hususlar:\n{missing_items}"

        else:
            status_label = "Uygun görünmüyor"
            summary = f"{rule_res.support_name} için gerekli mevzuat kriterleri sağlanamamıştır."
            failed_items = "\n".join([f"• {chk}" for chk in rule_res.failed_checks])
            reasons = f"Sağlanamayan Kriterler:\n{failed_items}"
            next_actions.append(
                "Mevzuat koşullarını ve desteklenen havza/ürün kriterlerini inceleyiniz."
            )

        return ExplanationResult(
            support_id=rule_res.support_id,
            support_name=rule_res.support_name,
            status=rule_res.status,
            status_label_tr=status_label,
            summary_tr=summary,
            detailed_reason_tr=reasons,
            missing_requirements_tr=missing_tr,
            next_actions_tr=next_actions,
            citations=citations,
        )


template_explainer = TemplateExplainer()
