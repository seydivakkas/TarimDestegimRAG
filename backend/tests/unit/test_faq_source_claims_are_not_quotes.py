"""Assistant search results are candidates, never official quotes without a proof route."""
from frontend_pc.services.faq_service import ask_assistant


class FakeApi:
    def ask(self, message: str, top_k: int):
        assert message == "ÇKS koşulu nedir?"
        assert top_k == 3
        return {
            "summary_answer_tr": "Ön değerlendirme açıklamasıdır.",
            "matched_chunks": [
                {
                    "source_id": "RG_FAKE",
                    "title": "Özgün olduğu doğrulanmamış aday kaynak",
                    "section": "MADDE 3",
                    "text": "<script>alert('fake quote')</script>",
                    "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
                },
                "Metin olarak dönen doğrulanmamış arama parçası",
            ],
        }


def test_faq_retrieval_never_presents_unverified_passage_as_official_quote():
    message, history = ask_assistant("ÇKS koşulu nedir?", [], client=FakeApi())
    assert message == ""
    rendered = history[-1]["content"]
    assert "Aday kaynak metinleri" in rendered
    assert "resmî alıntı değildir" in rendered
    assert "PDF’de işaretli cümleyi aç" not in rendered
    assert "Doğrulanmış Resmî Mevzuat Dayanakları" not in rendered
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "#page=2" not in rendered
