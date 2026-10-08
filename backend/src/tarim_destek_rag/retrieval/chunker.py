import re

from tarim_destek_rag.retrieval.models import DocumentChunk


class HeadingAwareChunker:
    """Mevzuat ve resmî rehber metinlerini madde/başlık bazında parçalara ayıran motor."""

    @staticmethod
    def chunk_regulation_text(
        source_id: str,
        title: str,
        text: str,
        year: int = 2026,
        url: str | None = None,
    ) -> list[DocumentChunk]:
        """Metni 'MADDE X' veya numaralı başlık kalıplarına göre parçalar."""
        # MADDE ayracı regex'i
        pattern = r"(MADDE\s+\d+[\s\S]*?)(?=MADDE\s+\d+|$)"
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))

        chunks: list[DocumentChunk] = []
        if matches:
            for idx, match in enumerate(matches, start=1):
                chunk_text = match.group(1).strip()
                # Madde başlığını çıkar (Örn: MADDE 4)
                first_line = chunk_text.splitlines()[0]
                section_name = first_line[:64] if first_line else f"MADDE {idx}"

                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{source_id}-CHUNK-{idx:03d}",
                        source_id=source_id,
                        title=title,
                        section=section_name,
                        year=year,
                        text=chunk_text,
                        url=url,
                    )
                )
        else:
            # Madde bulunamadıysa paragraflara böl (fallback)
            paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
            if not paragraphs:
                paragraphs = [text.strip()]

            for idx, p in enumerate(paragraphs, start=1):
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{source_id}-CHUNK-{idx:03d}",
                        source_id=source_id,
                        title=title,
                        section=f"BÖLÜM {idx}",
                        year=year,
                        text=p,
                        url=url,
                    )
                )

        return chunks
