import hmac
import re
from pathlib import Path
from urllib.parse import quote as url_quote
import json
import os
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
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

    return FullEvaluationResponse(
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
    # No rule-engine cache update, no 2026 demo rates overwritten, no trusted
    # old quotes relabeled as current law.
    return result


@app.get("/evidence/highlight/{sha256}", tags=["PDF Belge Kanıtı"])
def show_exact_pdf_evidence(
    sha256: str, page: int, quote: str,
) -> Response:
    """Read-only verifiable highlighted COPY; original PDF remains immutable."""
    from tarim_destek_rag.updates.pdf_evidence import (
        SHA_PATTERN, UnverifiableEvidence, highlighted_pdf_copy,
        locate_pdf_quote,
    )
    if not SHA_PATTERN.fullmatch(sha256) or not 1 <= page <= 2000:
        raise HTTPException(status_code=422, detail="Belge SHA veya PDF sayfası geçersiz")
    root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    file_path = root / "originals" / f"{sha256}.pdf"
    # Only content-addressed archived originals; no URL fetching or path traversal.
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


# P0-8B: evidence IDs resolve ONLY server-side registered official source
# documents. No arbitrary page URL, client-provided quad or guessed quote.
@app.get("/api/v1/grounding/evidence/{sentence_id}", tags=["PDF Hukuki Kanıt"])
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
    from tarim_destek_rag.database.models import DynamicRateModel
    from tarim_destek_rag.auto_updater.grounding_repository import load_grounded_sentence

    query = select(DynamicRateModel).where(
        DynamicRateModel.program_key == program_key,
        DynamicRateModel.production_year == year,
    )
    if crop_code:
        query = query.where(DynamicRateModel.crop_code == crop_code)

    rate_row = session.scalars(query).first()
    if rate_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"{year} yılı için '{program_key}' programına ait doğrulanmış PDF kanıtı bulunamadı.",
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


# P0-8C: compare ONLY exact original-PDF source sentences. This is a
# textual review report: never a determination of what is legally repealed.
from pydantic import BaseModel, Field


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
