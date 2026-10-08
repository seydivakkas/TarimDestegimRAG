import json
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from tarim_destek_rag.api.schemas import (
    ApiErrorResponse,
    AskQuestionRequest,
    AskQuestionResponse,
    FullEvaluationRequest,
    FullEvaluationResponse,
    SupportProgramDTO,
)
from tarim_destek_rag.calculator.calculator import (
    CalculationResult,
    SupportCalculator,
)
from tarim_destek_rag.database.connection import (
    SessionLocal,
    get_db_session,
    init_db,
)
from tarim_destek_rag.database.faq_repository import FAQRepository
from tarim_destek_rag.database.repository import SupportRepository
from tarim_destek_rag.explainer.template_explainer import (
    ExplanationResult,
    TemplateExplainer,
)
from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.models.source import SourceDefinition
from tarim_destek_rag.normalization.seed_data import seed_2026_support_data
from tarim_destek_rag.retrieval.assistant import assistant_engine
from tarim_destek_rag.retrieval.hybrid import hybrid_retriever
from tarim_destek_rag.retrieval.knowledge_base import (
    FARMER_FAQ_LIST,
    OFFICIAL_REGULATION_CHUNKS,
)
from tarim_destek_rag.retrieval.vector_store import vector_store
from tarim_destek_rag.rules.base import RuleResult
from tarim_destek_rag.rules.orchestrator import decision_orchestrator
from tarim_destek_rag.scraper.faq_harvester import AgriculturalFAQHarvester
from tarim_destek_rag.scraper.registry import SourceRegistry, source_registry


def seed_vector_store_data() -> None:
    """Mevzuat açıklamalarını vektör ve BM25 hibrit indeksine tohumlar."""
    # HybridRetriever her iki indeksi günceller; yoğun indekse ikinci kez eklemeyin.
    hybrid_retriever.add_chunks(OFFICIAL_REGULATION_CHUNKS)
    logger.info(
        "2026 Resmî mevzuat bilgi tabanı indekslendi (%d parça)",
        len(OFFICIAL_REGULATION_CHUNKS),
        extra={"component": "seed_vector_store_data"},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama açılışında veritabanını ve vektör indeksini hazırlar."""
    logger.info("TarımDestekRAG FastAPI servisi başlatılıyor...")
    init_db()

    try:
        loaded_reg = SourceRegistry.load_from_yaml("configs/sources.yaml")
        for s in loaded_reg.list_all():
            if s.id not in source_registry._sources:
                source_registry.register(s)
    except Exception as e:
        logger.warning("Kaynak kayıt defteri yükleme uyarısı: %s", e)

    with SessionLocal() as session:
        seed_2026_support_data(session)

    try:
        seed_vector_store_data()
    except Exception as e:
        logger.warning("Vektör mağazası tohumlanırken uyarı: %s", e)

    yield
    logger.info("TarımDestekRAG FastAPI servisi kapatılıyor.")


app = FastAPI(
    title="TarımDestekRAG API",
    version="1.0.0",
    description="Türkiye 2026 Bitkisel Üretim Destekleri Deterministik Karar ve Açıklama API'si",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiErrorResponse(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        ).model_dump(),
    )


@app.get("/", tags=["Sistem"])
def root_endpoint(request: Request):
    """Ana sayfa: Tarayıcılar için zengin HTML karşılama paneli, API istemcileri için JSON döner."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(
            """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌾 TarımDestekRAG 2026 — FastAPI Servisi</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b1320; color: #f1f5f9; padding: 40px; margin: 0; line-height: 1.6; }
        .card { background: #152238; border: 1px solid #1e3a5f; border-radius: 12px; padding: 32px; max-width: 680px; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { color: #10b981; margin-top: 0; font-size: 1.6rem; display: flex; align-items: center; justify-content: space-between; }
        .badge { background: #065f46; color: #a7f3d0; padding: 4px 12px; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; }
        p { color: #94a3b8; }
        .links { margin: 24px 0; }
        .links a { display: flex; align-items: center; justify-content: space-between; background: #1e293b; color: #38bdf8; text-decoration: none; padding: 14px 18px; margin: 10px 0; border-radius: 8px; border: 1px solid #334155; transition: 0.2s; font-weight: 500; }
        .links a:hover { background: #0f172a; border-color: #38bdf8; color: #7dd3fc; transform: translateY(-1px); }
        footer { margin-top: 24px; font-size: 0.8rem; color: #64748b; border-top: 1px solid #1e293b; padding-top: 16px; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h1><span>🌾 TarımDestekRAG API</span> <span class="badge">🟢 ÇALIŞIYOR (200 OK)</span></h1>
        <p>Türkiye 2026 Resmî Gazete Bitkisel Üretim Destekleri Karar Motoru & Mevzuat Servisi aktif durumdadır.</p>
        <div class="links">
            <a href="/docs"><span>📚 Interactive API Dokümantasyonu (Swagger UI)</span> <span>&rarr;</span></a>
            <a href="/redoc"><span>📖 ReDoc API Dokümantasyonu</span> <span>&rarr;</span></a>
            <a href="/health"><span>💓 Sistem Sağlık Kontrolü (/health)</span> <span>&rarr;</span></a>
            <a href="http://127.0.0.1:7860" target="_blank"><span>🌱 Gradio PC Web Kullanıcı Arayüzü (Port 7860)</span> <span>&rarr;</span></a>
        </div>
        <footer>
            Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas) — Özel Lisans (Tüm Hakları Saklıdır)
        </footer>
    </div>
</body>
</html>"""
        )
    return {
        "status": "ok",
        "service": "TarımDestekRAG API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health",
        "web_ui": "http://127.0.0.1:7860",
    }


@app.get("/health", tags=["Sistem"])
def health_check() -> dict[str, str]:
    """Sağlık kontrolü endpoint'i."""
    return {"status": "ok", "service": "TarımDestekRAG API", "version": "1.0.0"}


@app.post("/eligibility", response_model=list[RuleResult], tags=["Karar Motoru"])
def evaluate_eligibility(
    payload: FullEvaluationRequest, session: Session = Depends(get_db_session)
) -> list[RuleResult]:
    """Deterministik kural motoruyla 5 destek programı için uygunluk kararı üretir."""
    return decision_orchestrator.evaluate_all(payload.farmer, payload.parcel, session)


@app.post("/calculate", response_model=list[CalculationResult], tags=["Hesaplayıcı"])
def calculate_supports(
    payload: FullEvaluationRequest, session: Session = Depends(get_db_session)
) -> list[CalculationResult]:
    """Uygun görülen programlar için kuruş hassasiyetinde tutar hesabı yapar."""
    rule_results = decision_orchestrator.evaluate_all(payload.farmer, payload.parcel, session)
    support_repo = SupportRepository(session)

    calc_results: list[CalculationResult] = []
    for r in rule_results:
        amt_rec = support_repo.get_amount(r.support_id, payload.parcel.crop)
        unit_amt = amt_rec.unit_amount if amt_rec else None
        calc = SupportCalculator.calculate(r, payload.parcel.area_da, unit_amt)
        calc_results.append(calc)

    return calc_results


@app.post("/evaluate", response_model=FullEvaluationResponse, tags=["Uçtan Uca Değerlendirme"])
def evaluate_all(
    payload: FullEvaluationRequest, session: Session = Depends(get_db_session)
) -> FullEvaluationResponse:
    """Tek çağrıda kural işletimi, tutar hesabı ve Türkçe şablon açıklamaları birleştirir."""
    rule_results = decision_orchestrator.evaluate_all(payload.farmer, payload.parcel, session)
    support_repo = SupportRepository(session)

    calc_results: list[CalculationResult] = []
    explanations: list[ExplanationResult] = []
    total_amount = Decimal("0.00")

    for r in rule_results:
        amt_rec = support_repo.get_amount(r.support_id, payload.parcel.crop)
        unit_amt = amt_rec.unit_amount if amt_rec else None
        calc = SupportCalculator.calculate(r, payload.parcel.area_da, unit_amt)
        calc_results.append(calc)

        if calc.estimated_amount:
            total_amount += calc.estimated_amount

        try:
            matched = vector_store.search(f"{r.support_name} {payload.parcel.crop}", top_k=1)
            chunks = [m[0] for m in matched] if matched else None
        except Exception:
            chunks = None

        exp = TemplateExplainer.explain(r, calc, chunks)
        explanations.append(exp)

    return FullEvaluationResponse(
        farmer=payload.farmer,
        parcel=payload.parcel,
        rules=rule_results,
        calculations=calc_results,
        explanations=explanations,
        total_estimated_amount=total_amount,
    )


@app.post("/ask", response_model=AskQuestionResponse, tags=["Chatbot / Semantik Arama"])
def ask_question(payload: AskQuestionRequest) -> AskQuestionResponse:
    """Kullanıcı sorusuna hibrit arama ve deterministik mevzuat senteziyle yanıt döner."""
    try:
        summary_text, matched_chunks, source_titles = assistant_engine.answer_question(
            payload.question, top_k=payload.top_k
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantik arama hatası: {e}",
        ) from e

    return AskQuestionResponse(
        question=payload.question,
        summary_answer_tr=summary_text,
        matched_chunks=matched_chunks,
        source_titles=source_titles,
    )


@app.get("/faqs", tags=["Chatbot / Semantik Arama"])
def list_faqs(
    category: str | None = None,
    search: str | None = None,
    session: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Tarımsal Sıkça Sorulan Sorular (SSS) kütüphanesini veritabanından döner."""
    repo = FAQRepository(session)
    faqs = repo.list_faqs(category=category, search_query=search)
    if faqs:
        return [
            {
                "id": f.id,
                "category": f.category,
                "sub_category": f.sub_category,
                "question": f.question,
                "answer": f.answer,
                "citation": f.legal_citation,
                "source_name": f.source_name,
                "verified": f.verified,
                "keywords": json.loads(f.keywords) if f.keywords.startswith("[") else [f.keywords],
            }
            for f in faqs
        ]
    # Bellek içi liste yedeği (Fallback)
    result = FARMER_FAQ_LIST
    if category and category != "Tümü":
        result = [f for f in result if category.lower() in f.get("category", "").lower()]
    if search and search.strip():
        sq = search.strip().lower()
        result = [f for f in result if sq in f.get("question", "").lower() or sq in f.get("answer", "").lower()]
    return result


@app.get("/faqs/stats", tags=["Chatbot / Semantik Arama"])
def get_faq_stats(session: Session = Depends(get_db_session)) -> dict[str, Any]:
    """Tarımsal SSS veritabanı istatistiklerini döner."""
    repo = FAQRepository(session)
    stats = repo.get_stats()
    if stats["total_count"] == 0:
        return {
            "total_count": len(FARMER_FAQ_LIST),
            "verified_count": 0,  # Katalog kayıtları bağımsız resmî pasajla doğrulanmadı.
            "category_counts": {
                c: sum(1 for faq in FARMER_FAQ_LIST if faq["category"] == c)
                for c in {f["category"] for f in FARMER_FAQ_LIST}
            },
        }
    return stats


@app.post("/faqs/harvest", tags=["Chatbot / Semantik Arama"])
def harvest_faqs(session: Session = Depends(get_db_session)) -> dict[str, Any]:
    """Yerel küratörlü SSS verisini ekler; bu uç nokta web taraması yapmaz."""
    harvester = AgriculturalFAQHarvester(session)
    seeded_count = harvester.seed_initial_knowledge()
    new_chunks = harvester.export_as_document_chunks()
    if new_chunks:
        hybrid_retriever.add_chunks(new_chunks)
    return {
        "status": "SUCCESS",
        "message": "Yerel SSS kayıtları işlendi. Dış internet kaynağı taranmadı.",
        "seeded_count": seeded_count,
        "harvested_count": 0,
        "total_faqs": len(new_chunks),
        "indexed_chunks": len(new_chunks),
    }




@app.get("/supports", response_model=list[SupportProgramDTO], tags=["Destekler"])
def list_supports(
    year: int = 2026, session: Session = Depends(get_db_session)
) -> list[SupportProgramDTO]:
    """2026 yılı aktif destek programlarını ve başvuru pencerelerini listeler."""
    support_repo = SupportRepository(session)
    programs = support_repo.list_programs(year=year)

    dtos: list[SupportProgramDTO] = []
    for p in programs:
        w = support_repo.get_window(p.id, year=year)
        dtos.append(
            SupportProgramDTO(
                id=p.id,
                name=p.name,
                year=p.year,
                active=p.active,
                description=p.description,
                application_start=w.start_date if w else None,
                application_end=w.end_date if w else None,
            )
        )
    return dtos


@app.get("/sources", response_model=list[SourceDefinition], tags=["Kaynaklar"])
def list_sources() -> list[SourceDefinition]:
    """Kayıtlı resmî mevzuat kaynaklarını öncelik sırasına göre listeler."""
    return source_registry.list_active_sources()
