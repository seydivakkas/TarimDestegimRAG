from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Mevzuat ve açıklama metin parçacığı (Citation-Ready Chunk)."""

    chunk_id: str
    source_id: str
    title: str
    section: str = Field(default="GENEL", description="Madde veya bölüm adı")
    year: int = 2026
    text: str
    url: str | None = None
    effective_date: str = "2026-01-01"
