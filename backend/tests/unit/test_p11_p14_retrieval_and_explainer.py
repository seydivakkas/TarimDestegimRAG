from decimal import Decimal

from tarim_destek_rag.calculator.calculator import CalculationResult
from tarim_destek_rag.citations.verifier import CitationVerifier
from tarim_destek_rag.explainer.template_explainer import (
    CitationDetail,
    TemplateExplainer,
)
from tarim_destek_rag.models.source import AuthorityEnum, SourceDefinition
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.retrieval.chunker import HeadingAwareChunker
from tarim_destek_rag.retrieval.models import DocumentChunk
from tarim_destek_rag.rules.base import RuleResult
from tarim_destek_rag.scraper.registry import SourceRegistry


def test_heading_aware_chunker():
    """Mevzuat metninin MADDE başlıklarına göre ayrıştırılması."""
    text = (
        "MADDE 1 - Bu kararın amacı 2026 yılı bitkisel üretim desteklerini belirlemektir.\n\n"
        "MADDE 2 - Çiftçi Kayıt Sistemine dahil olan üreticilere temel destek verilir.\n\n"
        "MADDE 3 - Tarım havzalarında belirlenen stratejik ürünlere ilave destek sağlanır."
    )
    chunks = HeadingAwareChunker.chunk_regulation_text(
        source_id="RG-TEST",
        title="Test Mevzuat",
        text=text,
        year=2026,
    )
    assert len(chunks) == 3
    assert chunks[0].section.startswith("MADDE 1")
    assert "2026 yılı bitkisel" in chunks[0].text
    assert chunks[1].section.startswith("MADDE 2")


def test_template_explainer_eligible():
    """Uygun görünen karar için Türkçe şablon açıklama üretimi."""
    rule_res = RuleResult(
        rule_id="RULE_BASIC_SUPPORT_2026",
        support_id="BASIC_SUPPORT_2026",
        support_name="Temel Destek",
        status=EligibilityStatusEnum.ELIGIBLE,
        passed_checks=["ÇKS kaydı aktif", "2026 yılı buğday ekimi"],
        source_ids=["RG-2026-BITKISEL"],
    )
    calc_res = CalculationResult(
        support_id="BASIC_SUPPORT_2026",
        support_name="Temel Destek",
        status=EligibilityStatusEnum.ELIGIBLE,
        area_da=Decimal("20.0"),
        unit_amount=Decimal("465.00"),
        estimated_amount=Decimal("9300.00"),
        formula="20 da * 465 TL/da = 9300 TL",
    )

    chunk = DocumentChunk(
        chunk_id="CHK-01",
        source_id="RG-2026-BITKISEL",
        title="2026 Kararı",
        section="Madde 3",
        text="Temel destek mazot ve gübre tutarlarını kapsar.",
    )

    explanation = TemplateExplainer.explain(rule_res, calc_res, [chunk])
    assert explanation.status_label_tr == "Uygun görünüyor"
    assert "9,300.00 TL" in explanation.summary_tr
    assert len(explanation.citations) == 1
    assert explanation.citations[0].source_id == "RG-2026-BITKISEL"


def test_template_explainer_review():
    """Eksik alan durumunda (REVIEW) şablon açıklama üretimi."""
    rule_res = RuleResult(
        rule_id="RULE_BASIC_SUPPORT_2026",
        support_id="BASIC_SUPPORT_2026",
        support_name="Temel Destek",
        status=EligibilityStatusEnum.REVIEW,
        missing_fields=["cks_status"],
    )

    explanation = TemplateExplainer.explain(rule_res)
    assert explanation.status_label_tr == "Ek kontrol gerekiyor"
    assert len(explanation.missing_requirements_tr) > 0
    assert "ÇKS" in explanation.missing_requirements_tr[0]
    assert len(explanation.next_actions_tr) > 0


def test_citation_verifier():
    """Atıf doğrulayıcı geçerli ve geçersiz kaynak denetimi."""
    reg = SourceRegistry()
    reg.register(
        SourceDefinition(
            id="RG-2026-BITKISEL",
            url="https://resmigazete.gov.tr",
            authority=AuthorityEnum.OFFICIAL_GAZETTE,
            title="Resmî Gazete",
            active=True,
        )
    )

    verifier = CitationVerifier(registry=reg)

    valid_cit = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="Resmî Gazete",
        section="Madde 1",
        year=2026,
        snippet="Mevzuat metni",
    )
    v_res = verifier.verify(valid_cit)
    assert v_res.is_valid is True
    assert v_res.status == "VERIFIED"

    invalid_cit = CitationDetail(
        source_id="UNKNOWN-SOURCE",
        title="Bilinmeyen",
        section="Madde X",
        year=2026,
        snippet="...",
    )
    inv_res = verifier.verify(invalid_cit)
    assert inv_res.is_valid is False
    assert inv_res.status == "INSUFFICIENT_EVIDENCE"


def test_assistant_engine_crop_amounts():
    """Asistan motorunun ürün desteği ve tutar sorgusuna kesin yanıt vermesi testi."""
    from tarim_destek_rag.retrieval.assistant import assistant_engine
    from tarim_destek_rag.retrieval.knowledge_base import OFFICIAL_REGULATION_CHUNKS

    assistant_engine.retriever.add_chunks(OFFICIAL_REGULATION_CHUNKS)

    ans, chunks, _ = assistant_engine.answer_question("2026 buğday desteği ne kadar?")
    assert "BUĞDAY" in ans
    assert "465.00 TL/da" in ans
    assert "930.00 TL/da" in ans
    assert len(chunks) > 0


def test_assistant_engine_cks_guidance():
    """ÇKS başvuru süreci ve evraklar sorgusunun eksiksiz yanıtlanması testi."""
    from tarim_destek_rag.retrieval.assistant import assistant_engine

    ans, _, _ = assistant_engine.answer_question("ÇKS kaydı nasıl yapılır ve gerekli evraklar nelerdir?")
    assert "e-Devlet" in ans
    assert "İlçe Tarım" in ans
    assert "Ziraat Odası" in ans
    assert "31 Aralık 2026" in ans


def test_assistant_engine_women_young_farmer():
    """Kadın ve genç çiftçi ilave destek sorgusu testi."""
    from tarim_destek_rag.retrieval.assistant import assistant_engine

    ans, _, _ = assistant_engine.answer_question("Kadın çiftçilere ek destek veriliyor mu?")
    assert "%100" in ans
    assert "41 yaş" in ans
    assert "Kadın" in ans


def test_assistant_engine_water_constraint():
    """Yeraltı su kısıtı havzaları sorgusu testi."""
    from tarim_destek_rag.retrieval.assistant import assistant_engine

    ans, _, _ = assistant_engine.answer_question("Yeraltı su kısıtı desteği nedir?")
    assert "250 TL" in ans
    assert "Konya" in ans or "Mercimek" in ans or "Nohut" in ans


def test_assistant_engine_haciz_yasagi():
    """Haciz yasağı (Tarım Kanunu Md. 23) yasal sorgusu testi."""
    from tarim_destek_rag.retrieval.assistant import assistant_engine

    ans, _, _ = assistant_engine.answer_question("Tarımsal destekleme parasına haciz konulur mu?")
    assert "haczedilemez" in ans.lower() or "haciz konulamaz" in ans.lower()
    assert "23" in ans
    assert "Tarım Kanunu" in ans


def test_assistant_engine_kiralik_ve_hisseli_arazi():
    """Kiralık ve hisseli arazi ÇKS hakları sorgusu testi."""
    from tarim_destek_rag.retrieval.assistant import assistant_engine

    ans_kira, _, _ = assistant_engine.answer_question("Kiralık arazide ÇKS ve destek alınabilir mi?")
    assert "kira sözleşmesi" in ans_kira.lower()

    ans_hisse, _, _ = assistant_engine.answer_question("Hisseli tapuda diğer paydaşlar imza vermezse ne yapılır?")
    assert "taahhütname" in ans_hisse.lower()


def test_assistant_engine_expanded_crop_and_organic():
    """Genişletilmiş ürün kataloğu (Çeltik, vb.) ve organik tarım testi."""
    from tarim_destek_rag.retrieval.assistant import assistant_engine

    ans_celtik, _, _ = assistant_engine.answer_question("2026 çeltik desteği ne kadar?")
    assert "ÇELTİK" in ans_celtik
    assert "450.00 TL/da" in ans_celtik

    ans_org, _, _ = assistant_engine.answer_question("Organik tarım ve biyolojik mücadele desteği kimlere verilir?")
    assert "organik tarım" in ans_org.lower()


