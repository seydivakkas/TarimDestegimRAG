import hmac
import json
import os
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tarim_destek_rag.api.schemas import (
    ApiErrorResponse,
    AskQuestionRequest,
    AskQuestionResponse,
    FullEvaluationRequest,
    FullEvaluationResponse,
    HarvestLiveRequest,
    ModerationRejectRequest,
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
from tarim_destek_rag.scraper.pipeline import HarvestModerationService
from tarim_destek_rag.scraper.registry import SourceRegistry, source_registry


def seed_vector_store_data() -> None:
    """Mevzuat açıklamalarını vektör ve BM25 hibrit indeksine tohumlar."""
    if not hybrid_retriever.bm25_retriever._chunks:
        hybrid_retriever.bm25_retriever.add_chunks(OFFICIAL_REGULATION_CHUNKS)
    if not hybrid_retriever.dense_store._chunks:
        # Dense model may require downloads; BM25 is ready even if this fails.
        hybrid_retriever.dense_store.add_chunks(OFFICIAL_REGULATION_CHUNKS)
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
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "TARIM_RAG_CORS_ORIGINS", "http://localhost:7860,http://127.0.0.1:7860"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
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
        amt_rec = support_repo.get_amount(
            r.support_id, payload.parcel.crop,
            production_year=payload.parcel.production_year,
            province=payload.farmer.province, district=payload.farmer.district,
        )
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
        amt_rec = support_repo.get_amount(
            r.support_id, payload.parcel.crop,
            production_year=payload.parcel.production_year,
            province=payload.farmer.province, district=payload.farmer.district,
        )
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

    # No network I/O in evaluation: only return an original-PDF URL if the
    # exact Ministry source is installed and both source cell texts are found.
    from tarim_destek_rag.citations.basin_visual import lookup_basin_crop_evidence

    basin_evidence = lookup_basin_crop_evidence(
        payload.farmer.province, payload.farmer.district,
        payload.parcel.crop, payload.parcel.production_year,
    )
    return FullEvaluationResponse(
        basin_evidence=basin_evidence,
        farmer=payload.farmer,
        parcel=payload.parcel,
        rules=rule_results,
        calculations=calc_results,
        explanations=explanations,
        total_estimated_amount=(
            None if any(calc.status == "REVIEW" for calc in calc_results) else total_amount
        ),
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
            "verified_count": 0,
            "category_counts": {c: 1 for c in {f["category"] for f in FARMER_FAQ_LIST}},
        }
    return stats


def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    """Yazma uç noktasını güvenli varsayılanla (kapalı) koru."""
    expected = os.getenv("TARIM_RAG_ADMIN_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Yönetici yazma işlemleri yapılandırılmadı.")
    if x_admin_key is None or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=403, detail="Yönetici yetkisi gerekli.")


@app.post("/faqs/harvest", tags=["Chatbot / Semantik Arama"])
def harvest_faqs(
    session: Session = Depends(get_db_session),
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Gerçek web taraması değil: yalnızca yerleşik örnek SSS verisini yeniden yükler."""
    harvester = AgriculturalFAQHarvester(session)
    count = harvester.seed_initial_knowledge()
    new_chunks = harvester.export_as_document_chunks()
    if new_chunks:
        hybrid_retriever.add_chunks(new_chunks)
    return {
        "status": "SUCCESS",
        "message": f"Yerleşik SSS kayıtları yeniden yüklendi ({count} kayıt); web taraması yapılmadı.",
        "harvested_count": count,
        "total_faqs": count,
        "total_faqs_in_db": count,
        "indexed_chunks": len(new_chunks),
    }


@app.post("/faqs/harvest-live", tags=["Chatbot / Semantik Arama"])
def harvest_live_faqs(
    payload: HarvestLiveRequest,
    session: Session = Depends(get_db_session),
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """İzinli resmî adresten canlı tarama yapar, diff hesaplar ve PENDING inceleme kuyruğuna ekler."""
    service = HarvestModerationService(session)
    try:
        result = service.harvest_from_source(
            url=payload.source_url,
            admin_user="admin",
            source_name=payload.source_name,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Canlı tarama başarısız: {e}") from e


@app.get("/faqs/moderation-queue", tags=["Yönetim ve Moderasyon"])
def list_moderation_queue(
    status: str = "PENDING",
    session: Session = Depends(get_db_session),
    _admin: None = Depends(require_admin_key),
) -> list[dict[str, Any]]:
    """İnceleme kuyruğundaki kayıtları listeler."""
    repo = FAQRepository(session)
    items = repo.list_moderation_queue(status=status)
    return [
        {
            "id": item.id,
            "question": item.question,
            "answer": item.answer,
            "legal_citation": item.legal_citation,
            "legal_span": item.legal_span,
            "source_url": item.source_url,
            "source_domain": item.source_domain,
            "moderation_status": item.moderation_status,
            "version": item.version,
            "created_at": item.created_at,
        }
        for item in items
    ]


@app.post("/faqs/{faq_id}/approve", tags=["Yönetim ve Moderasyon"])
def approve_faq(
    faq_id: str,
    session: Session = Depends(get_db_session),
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Moderatör onayı ile kaydı yayına alır ve retriever indeksine ekler."""
    service = HarvestModerationService(session)
    try:
        approved = service.approve_item(faq_id, admin_user="admin", retriever=hybrid_retriever)
        return {
            "status": "APPROVED",
            "id": approved.id,
            "verified": approved.verified,
            "moderation_status": approved.moderation_status,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve)) from ve


@app.post("/faqs/{faq_id}/reject", tags=["Yönetim ve Moderasyon"])
def reject_faq(
    faq_id: str,
    payload: ModerationRejectRequest,
    session: Session = Depends(get_db_session),
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Moderatör tarafından kaydı gerekçeli olarak reddeder."""
    service = HarvestModerationService(session)
    try:
        rejected = service.reject_item(faq_id, reason=payload.reason, admin_user="admin")
        return {
            "status": "REJECTED",
            "id": rejected.id,
            "verified": rejected.verified,
            "moderation_status": rejected.moderation_status,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve)) from ve


@app.get("/faqs/moderation-logs", tags=["Yönetim ve Moderasyon"])
def get_moderation_logs(
    limit: int = 100,
    session: Session = Depends(get_db_session),
    _admin: None = Depends(require_admin_key),
) -> list[dict[str, Any]]:
    """Denetim günlüğü kayıtlarını döner."""
    repo = FAQRepository(session)
    logs = repo.get_audit_logs(limit=limit)
    return [
        {
            "id": record.id,
            "action": record.action,
            "faq_id": record.faq_id,
            "performed_by": record.performed_by,
            "timestamp": record.timestamp,
            "details": record.details,
        }
        for record in logs
    ]


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


# P0-8: manual discovery is separated from legal publication and only scans
# allowlisted official portals; a user cannot submit arbitrary URLs.
@app.post("/admin/legal-updates/scan", tags=["Gelecek Yıl Mevzuat Takibi"])
def scan_future_legal_changes(
    year: int,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    from tarim_destek_rag.updates.discovery import read_portals, scan_official_sources

    if not 2020 <= year <= 2100:
        raise HTTPException(status_code=422, detail="Geçersiz üretim yılı")
    portals = read_portals(Path("configs/official_update_portals.json"))
    result = scan_official_sources(
        production_year=year, portals=portals,
        output=Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
    )
    return result


class AnalyzeRawLegislationRequest(BaseModel):
    source_url: str
    text_or_base64: str
    mime_type: str = "text/html"


@app.get("/admin/legal-updates/legislation", tags=["Gelecek Yıl Mevzuat Takibi"])
def list_discovered_legislation(
    year: int | None = None,
    legislation_type: str | None = None,
    _admin: None = Depends(require_admin_key),
) -> list[dict[str, Any]]:
    """Taranıp yapısal olarak çözümlenmiş resmî mevzuat belgelerini listeler."""
    from tarim_destek_rag.updates.legislation_repository import LegislationCatalogRepository

    repo = LegislationCatalogRepository(
        Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    )
    return repo.list_all(year=year, legislation_type=legislation_type)


@app.get("/admin/legal-updates/legislation/{document_sha256}", tags=["Gelecek Yıl Mevzuat Takibi"])
def get_discovered_legislation_detail(
    document_sha256: str,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Belirli bir resmî mevzuat belgesinin maddelerini, ek tablolarını ve yürürlük tarihlerini döner."""
    from tarim_destek_rag.updates.legislation_repository import LegislationCatalogRepository

    repo = LegislationCatalogRepository(
        Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    )
    leg = repo.load(document_sha256)
    if leg is None:
        raise HTTPException(status_code=404, detail="Mevzuat kaydı bulunamadı")
    return leg.to_dict()


@app.post("/admin/legal-updates/analyze-raw", tags=["Gelecek Yıl Mevzuat Takibi"])
def analyze_raw_legislation(
    payload: AnalyzeRawLegislationRequest,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Resmî metni (HTML veya base64 PDF) anında yapısal analize tabi tutar."""
    import base64

    from tarim_destek_rag.updates.legislation_analyzer import LegislationAnalyzer

    raw_bytes = (
        base64.b64decode(payload.text_or_base64)
        if payload.mime_type == "application/pdf"
        else payload.text_or_base64.encode("utf-8")
    )
    analysis = LegislationAnalyzer.analyze_document(
        raw_bytes, payload.source_url, payload.mime_type
    )
    return analysis.to_dict()


@app.get("/evidence/highlight/basin/{sha256}", tags=["PDF Belge Kanıtı"])
def show_official_basin_crop_highlight(
    sha256: str, province: str, district: str, crop: str,
    production_year: int,
) -> Response:
    """Copy of original Ministry PDF with only selected district and crop marked."""
    from tarim_destek_rag.citations.basin_visual import highlight_basin_crop_copy
    from tarim_destek_rag.updates.pdf_evidence import SHA_PATTERN

    if not SHA_PATTERN.fullmatch(sha256):
        raise HTTPException(status_code=422, detail="Geçersiz resmî belge SHA-256")
    try:
        marked = highlight_basin_crop_copy(
            province, district, crop, production_year, expected_sha256=sha256,
        )
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        raise HTTPException(
            status_code=409,
            detail="Seçilen ilçe ve ürünün özgün PDF hücresi doğrulanamadı",
        ) from exc
    return Response(
        content=marked,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="resmi-havza-ilce-urun-isaretli.pdf"',
            "Cache-Control": "private, no-store",
            "X-Original-Source-SHA256": sha256,
            "X-Legal-Evidence": "ORIGINAL_PDF_ROW_AND_CROP_LOCATED_DRAFT_REVIEW",
        },
    )


@app.get("/evidence/highlight/visual/{sha256}", tags=["PDF Belge Kanıtı"])
def show_scanned_gazette_visual_clause(
    sha256: str, support_id: str,
) -> Response:
    """Serve original Gazette PDF COPY with manually located image-text area.

    Source image matches a reviewed original byte hash. Visual transcript
    location is not independently or legally approved.
    """
    from tarim_destek_rag.citations.visual_pdf import render_visual_pdf_copy
    from tarim_destek_rag.updates.pdf_evidence import SHA_PATTERN

    if not SHA_PATTERN.fullmatch(sha256):
        raise HTTPException(status_code=422, detail="Geçersiz özgün PDF SHA-256")
    try:
        highlighted = render_visual_pdf_copy(
            support_id, expected_sha256=sha256,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=409,
            detail="Özgün resmî PDF veya görsel pasaj koordinatı doğrulanamadı",
        ) from exc
    return Response(
        content=highlighted,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="resmi-gazete-8859-isaretli-kopya.pdf"',
            "Cache-Control": "private, no-store",
            "X-Original-Source-SHA256": sha256,
            "X-Legal-Evidence": "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW",
        },
    )


@app.get("/evidence/highlight/{sha256}", tags=["PDF Belge Kanıtı"])
def show_exact_pdf_evidence(
    sha256: str, page: int, quote: str,
) -> Response:
    """Read-only verifiable highlighted COPY; original PDF remains immutable."""
    from tarim_destek_rag.updates.pdf_evidence import (
        SHA_PATTERN,
        UnverifiableEvidence,
        highlighted_pdf_copy,
        locate_pdf_quote,
    )
    if not SHA_PATTERN.fullmatch(sha256) or not 1 <= page <= 2000:
        raise HTTPException(status_code=422, detail="Belge SHA veya PDF sayfası geçersiz")
    root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    file_path = root / "originals" / f"{sha256}.pdf"
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Bu belge sürümü arşivde bulunamadı")
    try:
        original = file_path.read_bytes()
        evidence = locate_pdf_quote(
            original, expected_sha256=sha256,
            page_1_indexed=page, exact_quote=quote,
        )
        marked_copy = highlighted_pdf_copy(original, evidence)
    except UnverifiableEvidence as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(
        content=marked_copy,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="legal-evidence-highlight.pdf"',
            "Cache-Control": "private, no-store",
            "X-Legal-Evidence": "EXACT_TEXT_LOCATED_PENDING_LEGAL_REVIEW",
            "X-Original-Source-SHA256": sha256,
        },
    )


# P0-8B/8C: Exact-sentence layout grounding & signed legal releases
@app.get("/api/v1/grounding/evidence/{sentence_id}", tags=["PDF Hukuki Kanıt"])
@app.get("/api/v1/grounding/{sentence_id}", tags=["PDF Hukuki Kanıt"])
def get_grounding_evidence(
    sentence_id: int,
    year: int,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Return original official PDF page, true quote and rectangles; DRAFT only."""
    from tarim_destek_rag.auto_updater.grounding_repository import load_grounded_sentence

    try:
        record, document, grounded, _ = load_grounded_sentence(
            session,
            archive_root=Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
            evidence_id=sentence_id, year=year,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "status": "DRAFT_NEEDS_HUMAN_LEGAL_REVIEW",
        "source_id": document.source_id,
        "source_url": document.original_url,
        "production_year": document.production_year,
        "original_pdf_sha256": grounded.document_sha256,
        "sentence_id": record.id,
        "article": record.article_no,
        "paragraph": record.paragraph_no,
        "clause": record.clause_no,
        "page_number": grounded.page_number,
        "exact_quote": grounded.exact_quote,
        "bounding_boxes": grounded.to_dict()["bounding_boxes"],
        "normalized_quads": grounded.normalized_quads,
        "highlighted_image_url": (
            f"/api/v1/grounding/image/{record.id}/page/{grounded.page_number}?year={year}"
        ),
        "legal_approval": False,
        "payable_amount": None,
    }


@app.get("/api/v1/grounding/image/{sentence_id}/page/{page_number}", tags=["PDF Hukuki Kanıt"])
def render_grounding_page(
    sentence_id: int,
    page_number: int,
    year: int,
    fmt: str = "png",
    session: Session = Depends(get_db_session),
) -> Response:
    """Draw true sentence highlight on exact original PDF page as PNG/WebP."""
    from tarim_destek_rag.auto_updater.grounding_repository import load_grounded_sentence
    from tarim_destek_rag.auto_updater.pdf_grounding import PDFGroundingEngine
    from tarim_destek_rag.updates.pdf_evidence import UnverifiableEvidence

    try:
        row, document, grounded, original = load_grounded_sentence(
            session,
            archive_root=Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
            evidence_id=sentence_id, year=year,
        )
        if grounded.page_number != page_number:
            raise ValueError("Requested PDF page does not match verified sentence")
        content, mime = PDFGroundingEngine.render_highlighted_page(
            original, grounded, image_format=fmt,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, FileNotFoundError, UnverifiableEvidence) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(
        content=content, media_type=mime,
        headers={
            "Cache-Control": "private, no-store",
            "X-Original-Source-SHA256": grounded.document_sha256,
            "X-Legal-Evidence": "DRAFT_EXACT_TEXT_NOT_APPROVED",
        },
    )


@app.get("/api/v1/grounding/program/{program_key}", tags=["PDF Hukuki Kanıt"])
def get_grounding_by_program(
    program_key: str,
    year: int,
    crop_code: str | None = None,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    from sqlalchemy import select

    from tarim_destek_rag.auto_updater.grounding_repository import load_grounded_sentence
    from tarim_destek_rag.database.models import DynamicRateModel

    query = select(DynamicRateModel).where(
        DynamicRateModel.program_key == program_key,
        DynamicRateModel.production_year == year,
    )
    if crop_code:
        query = query.where(DynamicRateModel.crop_code == crop_code)

    matching_rates = session.scalars(query.limit(2)).all()
    if not matching_rates:
        raise HTTPException(
            status_code=404,
            detail=f"{year} yılı için '{program_key}' programına ait doğrulanmış PDF kanıtı bulunamadı.",
        )
    if len(matching_rates) != 1:
        raise HTTPException(
            status_code=409,
            detail="Birden çok program/ürün/yıl kaydı bulundu; kaynak kanıtı belirsiz.",
        )
    rate_row = matching_rates[0]
    if rate_row.review_status != "DRAFT":
        raise HTTPException(
            status_code=409,
            detail="Oran adayı DRAFT durumunda değil; kanıt incelemesi reddedildi.",
        )

    try:
        record, document, grounded, _ = load_grounded_sentence(
            session,
            archive_root=Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
            evidence_id=rate_row.source_sentence_id,
            year=year,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "status": "DRAFT_NEEDS_HUMAN_LEGAL_REVIEW",
        "program_key": program_key,
        "crop_code": rate_row.crop_code,
        "production_year": year,
        "proposed_unit_amount": str(rate_row.proposed_unit_amount),
        "source_id": document.source_id,
        "source_url": document.original_url,
        "original_pdf_sha256": grounded.document_sha256,
        "sentence_id": record.id,
        "article": record.article_no,
        "paragraph": record.paragraph_no,
        "clause": record.clause_no,
        "page_number": grounded.page_number,
        "exact_quote": grounded.exact_quote,
        "bounding_boxes": grounded.to_dict()["bounding_boxes"],
        "normalized_quads": grounded.normalized_quads,
        "highlighted_image_url": (
            f"/api/v1/grounding/image/{record.id}/page/{grounded.page_number}?year={year}"
        ),
        "legal_approval": False,
        "payable_amount": None,
    }


class LegalDiffRequest(BaseModel):
    previous_year: int = Field(ge=2020, le=2100)
    target_year: int = Field(ge=2020, le=2100)
    previous_sentence_ids: list[int] = Field(min_length=1, max_length=300)
    current_sentence_ids: list[int] = Field(min_length=1, max_length=300)


@app.post("/admin/legal-updates/diff", tags=["Mevzuat Metin Farkı"])
def inspect_registered_legal_diff(
    request: LegalDiffRequest,
    session: Session = Depends(get_db_session),
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    from tarim_destek_rag.auto_updater.legal_diff_repository import report_from_evidence

    try:
        return report_from_evidence(
            session,
            archive_root=Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
            previous_year=request.previous_year, target_year=request.target_year,
            previous_sentence_ids=request.previous_sentence_ids,
            current_sentence_ids=request.current_sentence_ids,
        )
    except (ValueError, LookupError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/v1/legal-releases/{year}", tags=["Onaylı Mevzuat Sürümleri"])
def inspect_signed_year_release(
    year: int,
    as_of: date | None = None,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Read-only release-status proof. Not a farmer eligibility decision."""
    from tarim_destek_rag.auto_updater.release import resolve_active_release

    evaluation_date = as_of or date.today()
    result, _manifest = resolve_active_release(
        session, year=year, when=evaluation_date,
        archive_root=Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
    )
    return {
        "year": year,
        "as_of": evaluation_date.isoformat(),
        "status": result.status,
        "reason": result.reason,
        "release_id": result.release_id,
        "manifest_sha256": result.manifest_sha256,
        "farmer_eligibility_verified": False,
        "payable_amount": None,
    }


class SynthesizeRulesRequest(BaseModel):
    document_sha256: str
    production_year: int | None = None
    default_base_coefficient: str | None = None


@app.post("/admin/rules/synthesize", tags=["Dinamik Kural ve Fiyat Motoru"])
def synthesize_dynamic_rules(
    request: SynthesizeRulesRequest,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Keşfedilen mevzuattan ve ek tablolardan dinamik kuralları sentezler ve kaydeder."""
    from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository
    from tarim_destek_rag.rules.rule_synthesizer import RuleSynthesizer
    from tarim_destek_rag.rules.table_parser import TableParser
    from tarim_destek_rag.updates.legislation_repository import LegislationCatalogRepository

    archive_root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    leg_repo = LegislationCatalogRepository(archive_root)
    discovered = leg_repo.load(request.document_sha256)
    if discovered is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mevzuat belgesi bulunamadı: {request.document_sha256}",
        )

    base_coef = (
        Decimal(request.default_base_coefficient)
        if request.default_base_coefficient
        else Decimal("244.00")
    )
    year = (
        request.production_year
        or (discovered.effective_dates.valid_production_years[0]
            if discovered.effective_dates.valid_production_years else 2026)
    )

    # Ek tabloları ayrıştır
    matrix = TableParser.parse_annex_matrices(
        discovered.annex_tables,
        pages_text=[],
        production_year=year,
        default_base_coef=base_coef,
    )

    # Kuralları sentezle
    candidates = RuleSynthesizer.synthesize_candidates(
        discovered, matrix=matrix, production_year=year
    )

    # Kataloğa kaydet
    rule_repo = DynamicRuleRepository(archive_root)
    rule_repo.save_rules(year, candidates)

    return {
        "status": "SYNTHESIZED_SUCCESSFULLY",
        "document_sha256": request.document_sha256,
        "production_year": year,
        "base_coefficient": str(matrix.base_coefficient),
        "rule_count": len(candidates),
        "rules_sample": candidates[:5],
    }


@app.get("/admin/rules/dynamic", tags=["Dinamik Kural ve Fiyat Motoru"])
def list_dynamic_rules(
    year: int | None = None,
    program_key: str | None = None,
    crop_code: str | None = None,
    review_status: str | None = None,
    _admin: None = Depends(require_admin_key),
) -> list[dict[str, Any]]:
    """Kayıtlı dinamik kuralları listeler ve filtreler."""
    from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository

    archive_root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    rule_repo = DynamicRuleRepository(archive_root)
    return rule_repo.list_rules(
        year=year,
        program_key=program_key,
        crop_code=crop_code,
        review_status=review_status,
    )


class DynamicEvaluateRequest(BaseModel):
    production_year: int = Field(ge=2020, le=2100)
    as_of_date: str | None = None
    crop: str
    area_da: float = Field(gt=0)
    province: str
    district: str
    cks_registered: bool = True
    irrigation: bool = False
    certified_seed: bool = False
    certified_sapling: bool = False


@app.post("/api/v1/rules/dynamic-evaluate", tags=["Dinamik Kural ve Fiyat Motoru"])
def dynamic_evaluate_parcel(
    request: DynamicEvaluateRequest,
) -> dict[str, Any]:
    """Çiftçi parselini bitemporal dinamik kurallarla tüm destek programları bazında değerlendirir."""
    from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository
    from tarim_destek_rag.rules.dynamic_support_evaluator import DynamicSupportEvaluator

    archive_root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    rule_repo = DynamicRuleRepository(archive_root)
    catalog = rule_repo.get_catalog(years=[request.production_year])

    eval_date = (
        date.fromisoformat(request.as_of_date)
        if request.as_of_date
        else date(request.production_year, 6, 1)
    )

    summary = DynamicSupportEvaluator.evaluate_parcel(
        catalog=catalog,
        production_year=request.production_year,
        as_of_date=eval_date,
        crop=request.crop,
        area_da=Decimal(str(request.area_da)),
        province=request.province,
        district=request.district,
        cks_registered=request.cks_registered,
        irrigation=request.irrigation,
        certified_seed=request.certified_seed,
        certified_sapling=request.certified_sapling,
    )
    return summary.to_dict()


# ---------------------------------------------------------------------------
# P0-12: Çift Onaylı Hukuki İnceleme & WORM Aktivasyon Hattı Uç Noktaları
# ---------------------------------------------------------------------------

class CreateAttestationRequest(BaseModel):
    production_year: int = Field(ge=2020, le=2100)
    actor_id: str
    role: str  # "LEGAL_REVIEWER" veya "LEGAL_APPROVER"
    private_key_b64: str
    source_document_sha256: str | None = None
    statement: str | None = None
    notes: str = ""


class ActivateRulesRequest(BaseModel):
    production_year: int = Field(ge=2020, le=2100)
    source_document_sha256: str
    reviewer_attestation: dict[str, Any]
    approver_attestation: dict[str, Any]
    trusted_keys: dict[str, Any] | None = None


class RevokeRulesRequest(BaseModel):
    production_year: int = Field(ge=2020, le=2100)
    actor_id: str
    reason: str
    signature_b64: str | None = None


@app.post("/admin/rules/attestation", tags=["Çift Onaylı Hukuki Aktivasyon & WORM"])
def create_legal_attestation(
    request: CreateAttestationRequest,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Yetkilinin Ed25519 özel anahtarı ile kanonik beyanı imzalar ve tasdik nesnesi döner."""
    from datetime import UTC, datetime

    from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository
    from tarim_destek_rag.rules.legal_activation import (
        STANDARD_ATTESTATION_STATEMENT,
        LegalAttestation,
        build_canonical_manifest_bytes,
        sign_payload_ed25519,
    )
    from tarim_destek_rag.updates.legislation_repository import LegislationCatalogRepository

    archive_root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    rule_repo = DynamicRuleRepository(archive_root)
    rules = rule_repo.load_rules(request.production_year)
    if not rules:
        raise HTTPException(
            status_code=400,
            detail=f"{request.production_year} yılı için kayıtlı dinamik kural bulunamadı.",
        )

    doc_sha = request.source_document_sha256
    if not doc_sha:
        leg_repo = LegislationCatalogRepository(archive_root)
        discovered_docs = leg_repo.list_discovered(year=request.production_year)
        if not discovered_docs:
            discovered_docs = leg_repo.list_discovered()
        if not discovered_docs:
            raise HTTPException(
                status_code=400,
                detail="Mevzuat belgesi bulunamadı. Lütfen source_document_sha256 belirtin.",
            )
        doc_sha = discovered_docs[0].document_sha256

    rules_digest = rule_repo.compute_rules_digest(request.production_year)
    statement = request.statement or STANDARD_ATTESTATION_STATEMENT.format(year=request.production_year)

    canonical_bytes = build_canonical_manifest_bytes(
        production_year=request.production_year,
        source_document_sha256=doc_sha,
        rules_digest=rules_digest,
        rule_count=len(rules),
        statement=statement,
    )

    try:
        import base64

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        priv_raw = base64.b64decode(request.private_key_b64.encode("ascii"))
        private_key = Ed25519PrivateKey.from_private_bytes(priv_raw)
        pub_raw = private_key.public_key().public_bytes_raw()
        pub_b64 = base64.b64encode(pub_raw).decode("ascii")

        sig_b64 = sign_payload_ed25519(request.private_key_b64, canonical_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Ed25519 imzalama hatası: {exc}",
        )

    now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    attestation = LegalAttestation(
        actor_id=request.actor_id,
        role=request.role,
        public_key_b64=pub_b64,
        signature_b64=sig_b64,
        signed_at=now_utc,
        statement=statement,
        notes=request.notes,
    )
    return {
        "status": "ATTESTED_SUCCESSFULLY",
        "attestation": attestation.to_dict(),
        "source_document_sha256": doc_sha,
        "rules_digest": rules_digest,
        "rule_count": len(rules),
    }


@app.post("/admin/rules/activate", tags=["Çift Onaylı Hukuki Aktivasyon & WORM"])
def activate_dynamic_rules(
    request: ActivateRulesRequest,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Çift onaylı hukuki incelemeyi doğrular ve kuralları VERIFIED statüsüne yükseltir."""
    from tarim_destek_rag.rules.legal_activation import (
        ActivationError,
        InvalidSignatureError,
        LegalAttestation,
        RuleActivationPipeline,
        SeparationOfDutiesViolation,
        TrustedKeyMismatchError,
    )
    from tarim_destek_rag.rules.worm_audit import TamperedAuditError

    archive_root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    pipeline = RuleActivationPipeline(archive_root)

    try:
        rev_att = LegalAttestation.from_dict(request.reviewer_attestation)
        app_att = LegalAttestation.from_dict(request.approver_attestation)

        manifest = pipeline.activate_rules(
            production_year=request.production_year,
            reviewer_attestation=rev_att,
            approver_attestation=app_att,
            source_document_sha256=request.source_document_sha256,
            trusted_keys=request.trusted_keys,
        )
        return {
            "status": "ACTIVATED_SUCCESSFULLY",
            "production_year": request.production_year,
            "manifest": manifest.to_dict(),
        }
    except SeparationOfDutiesViolation as e:
        raise HTTPException(status_code=400, detail=f"Görevler Ayrılığı İhlali: {e}")
    except (InvalidSignatureError, TrustedKeyMismatchError) as e:
        raise HTTPException(status_code=403, detail=f"Kriptografik Doğrulama Reddedildi: {e}")
    except TamperedAuditError as e:
        raise HTTPException(status_code=500, detail=f"WORM Denetim İzi Bütünlük Hatası: {e}")
    except ActivationError as e:
        raise HTTPException(status_code=400, detail=f"Aktivasyon Hatası: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Beklenmeyen aktivasyon hatası: {e}")


@app.get("/admin/rules/activation-status", tags=["Çift Onaylı Hukuki Aktivasyon & WORM"])
def get_rule_activation_status(
    year: int = 2026,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Üretim yılına ait kural aktivasyon durumunu ve WORM zincir bütünlüğünü sorgular."""
    from tarim_destek_rag.rules.legal_activation import RuleActivationPipeline

    archive_root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    pipeline = RuleActivationPipeline(archive_root)
    return pipeline.get_activation_status(year)


@app.post("/admin/rules/revoke", tags=["Çift Onaylı Hukuki Aktivasyon & WORM"])
def revoke_rule_activation(
    request: RevokeRulesRequest,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Aktivasyonu derhal iptal eder (Fail-Closed: VERIFIED -> REVOKED) ve WORM günlüğüne yazar."""
    from tarim_destek_rag.rules.legal_activation import RuleActivationPipeline

    archive_root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    pipeline = RuleActivationPipeline(archive_root)
    pipeline.revoke_activation(
        production_year=request.production_year,
        actor_id=request.actor_id,
        reason=request.reason,
        signature_b64=request.signature_b64,
    )
    return {
        "status": "REVOKED_SUCCESSFULLY",
        "production_year": request.production_year,
        "reason": request.reason,
        "revoked_by": request.actor_id,
    }


@app.get("/admin/rules/worm-audit", tags=["Çift Onaylı Hukuki Aktivasyon & WORM"])
def get_worm_audit_log(
    year: int | None = None,
    event_type: str | None = None,
    limit: int = 50,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """WORM değiştirilemez denetim kütüğünü ve blok zincir doğrulama sonucunu döner."""
    from tarim_destek_rag.rules.worm_audit import WormAuditLog

    archive_root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    worm = WormAuditLog(archive_root)
    verified, message = worm.verify_chain()
    history = worm.get_history(production_year=year, event_type=event_type, limit=limit)
    return {
        "verified": verified,
        "message": message,
        "total_returned": len(history),
        "history": history,
    }


# ---------------------------------------------------------------------------
# P0-13: Gerçek Kurumsal Onay, HSM/KMS ve Güvenli Yayın Uç Noktaları
# ---------------------------------------------------------------------------

class BuildReleaseRequest(BaseModel):
    production_year: int = Field(default=2026, ge=2020, le=2100)
    key_alias: str = "release-master"
    enforce_verified_only: bool = True


class VerifyReleaseRequest(BaseModel):
    package_path: str
    expected_key_alias: str | None = "release-master"


class EnterpriseRevokeRequest(BaseModel):
    rule_id: str
    reason_code: str
    legal_reference: str
    authorized_officer: str
    notes: str = ""
    key_alias: str = "legal-approver"


@app.get("/admin/enterprise/kms/status", tags=["Kurumsal Onay & Güvenli Yayın (P0-13)"])
def get_kms_status(
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """KMS / HSM donanım güvenlik modülü durumunu ve kayıtlı anahtarları listeler."""
    from tarim_destek_rag.security.kms_provider import get_kms_provider

    kms = get_kms_provider()
    keys = kms.list_keys()
    return {
        "provider_type": type(kms).__name__,
        "key_count": len(keys),
        "keys": [
            {
                "key_id": k.key_id,
                "alias": k.alias,
                "algorithm": k.algorithm,
                "created_at_utc": k.created_at_utc,
                "is_enabled": k.is_enabled,
                "hardware_backed": k.hardware_backed,
                "public_key_b64": k.public_key_b64,
            }
            for k in keys
        ],
    }


@app.get("/admin/enterprise/db-roles/audit", tags=["Kurumsal Onay & Güvenli Yayın (P0-13)"])
def audit_database_roles(
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """PostgreSQL kurumsal rol ve RLS ayrım matrisini denetler."""
    from tarim_destek_rag.security.database_roles import get_database_role_manager

    manager = get_database_role_manager()
    return manager.audit_roles()


@app.post("/admin/enterprise/release/build", tags=["Kurumsal Onay & Güvenli Yayın (P0-13)"])
def build_secure_release(
    request: BuildReleaseRequest,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """KMS mühürlü güvenli yayın paketi oluşturur (.tar.gz)."""
    from tarim_destek_rag.security.secure_release import get_secure_release_manager

    rel_mgr = get_secure_release_manager()
    try:
        archive_path = rel_mgr.build_release_package(
            production_year=request.production_year,
            key_alias=request.key_alias,
            enforce_verified_only=request.enforce_verified_only,
        )
        return {
            "status": "SEALED_SUCCESSFULLY",
            "production_year": request.production_year,
            "archive_path": str(archive_path),
            "archive_name": archive_path.name,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Yayın paketi oluşturma hatası: {exc}")


@app.post("/admin/enterprise/release/verify", tags=["Kurumsal Onay & Güvenli Yayın (P0-13)"])
def verify_secure_release(
    request: VerifyReleaseRequest,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """KMS mühürlü yayın paketini fail-closed kriptografik doğrulamadan geçirir."""
    from tarim_destek_rag.security.secure_release import get_secure_release_manager

    rel_mgr = get_secure_release_manager()
    pkg_path = Path(request.package_path)
    is_valid, reason, metadata = rel_mgr.verify_release_package(
        package_path=pkg_path,
        expected_key_alias=request.expected_key_alias,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Kriptografik Doğrulama Reddedildi: {reason}")
    return {
        "status": "VERIFIED",
        "reason": reason,
        "metadata": metadata,
    }


@app.post("/admin/enterprise/revoke/enterprise", tags=["Kurumsal Onay & Güvenli Yayın (P0-13)"])
def enterprise_revoke_rule(
    request: EnterpriseRevokeRequest,
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Hukuki gerekçe taksonomisi ve KMS imzalı sertifika ile kuralı derhal iptal eder."""
    from tarim_destek_rag.security.revocation_manager import get_enterprise_revocation_manager

    rev_mgr = get_enterprise_revocation_manager()
    try:
        cert = rev_mgr.revoke_rule(
            rule_id=request.rule_id,
            reason_code=request.reason_code,
            legal_reference=request.legal_reference,
            authorized_officer=request.authorized_officer,
            notes=request.notes,
            key_alias=request.key_alias,
        )
        return {
            "status": "REVOKED_SUCCESSFULLY",
            "certificate": cert.to_dict(),
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"İptal işlemi hatası: {exc}")


@app.get("/admin/enterprise/evidence-vault/export", tags=["Kurumsal Onay & Güvenli Yayın (P0-13)"])
def export_evidence_vault(
    production_year: int = 2026,
    signer_officer: str = "ChiefLegalAuditor",
    key_alias: str = "legal-approver",
    _admin: None = Depends(require_admin_key),
) -> dict[str, Any]:
    """Mahkeme ve resmi denetime hazır imzalı Hukuki Delil Paketi (ZIP) dışa aktarır."""
    from tarim_destek_rag.security.enterprise_worm import get_enterprise_worm_archive

    archive = get_enterprise_worm_archive()
    try:
        zip_path = archive.export_legal_evidence_vault(
            production_year=production_year,
            signer_officer=signer_officer,
            key_alias=key_alias,
        )
        return {
            "status": "EVIDENCE_VAULT_EXPORTED",
            "production_year": production_year,
            "vault_path": str(zip_path),
            "vault_filename": zip_path.name,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Delil paketi oluşturma hatası: {exc}")



