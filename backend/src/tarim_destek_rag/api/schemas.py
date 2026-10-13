from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from tarim_destek_rag.calculator.calculator import CalculationResult
from tarim_destek_rag.explainer.template_explainer import ExplanationResult
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, Parcel
from tarim_destek_rag.rules.base import RuleResult


class FullEvaluationRequest(BaseModel):
    """Kapsamlı değerlendirme isteği (Çiftçi + Parsel)."""

    farmer: FarmerProfile
    parcel: Parcel


class FullEvaluationResponse(BaseModel):
    """Uygunluk, hesaplama ve açıklama birleşik yanıtı."""

    farmer: FarmerProfile
    parcel: Parcel
    rules: list[RuleResult]
    calculations: list[CalculationResult]
    explanations: list[ExplanationResult]
    total_estimated_amount: Decimal | None


class AskQuestionRequest(BaseModel):
    """Chatbot / Semantik Arama Soru İsteği."""

    question: str = Field(..., min_length=2, description="Kullanıcının doğal dil sorusu")
    top_k: int = Field(default=3, ge=1, le=10)


class DocumentUploadRequest(BaseModel):
    """Local document import, independent of official Gazette identity."""

    filename: str = Field(..., min_length=1, max_length=200)
    data_base64: str = Field(..., min_length=4, max_length=34_000_000)
    run_ocr: bool = False


class DocumentAskRequest(BaseModel):
    """Document exploration, not an eligibility or payment decision."""

    question: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(default=4, ge=1, le=10)
    source_id: str | None = Field(default=None, max_length=96)


class AskQuestionResponse(BaseModel):
    """Chatbot / Semantik Arama Yanıtı (Zero LLM - Doğrulanmış Mevzuat Metni)."""

    question: str
    summary_answer_tr: str
    matched_chunks: list[dict[str, Any]]
    source_titles: list[str]


class SupportProgramDTO(BaseModel):
    """Destekleme programı aktarım nesnesi."""

    id: str
    name: str
    year: int
    active: bool
    description: str | None = None
    application_start: str | None = None
    application_end: str | None = None


class ApiErrorResponse(BaseModel):
    """Standart API hata sözleşmesi."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class HarvestLiveRequest(BaseModel):
    """Canlı resmî kaynak tarama isteği."""

    source_url: str = Field(..., description="Taranacak izinli HTTPS resmî mevzuat/SSS adresi")
    source_name: str = Field(default="Resmî Tarım Portalı", description="Kaynağın resmî adı")


class ModerationRejectRequest(BaseModel):
    """Moderatör ret gerekçesi isteği."""

    reason: str = Field(..., min_length=3, description="Reddetme gerekçesi")
