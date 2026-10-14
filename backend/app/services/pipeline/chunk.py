"""
app/services/pipeline/chunk.py
──────────────────────────────────────────────────────────────────────
Reusable chunking logic, generalized from scripts/chunk_and_embed.py.
Same algorithm and chunk metadata shape as Phase 2 — just parameterized
by website_id and a list of already-scraped pages instead of reading
from local .txt files.
──────────────────────────────────────────────────────────────────────
"""

from datetime import datetime, timezone
from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def _split_into_chunks(text: str) -> list[str]:
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + CHUNK_SIZE
        if end >= text_len:
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        slice_text = text[start:end]
        last_period = slice_text.rfind(". ")
        if last_period > CHUNK_SIZE // 2:
            actual_end = start + last_period + 2
        else:
            last_space = slice_text.rfind(" ")
            actual_end = start + last_space if last_space > 0 else end

        chunk = text[start:actual_end].strip()
        if chunk:
            chunks.append(chunk)

        start = actual_end - CHUNK_OVERLAP

    return chunks


def chunk_pages(website_id: str, pages: list[dict]) -> list[dict]:
    """
    pages: [{ "url", "page_type", "text" }, ...]
    Returns chunk records ready for embedding — same shape as Phase 2's
    chunks.json entries.
    """
    scraped_at = datetime.now(timezone.utc).isoformat()
    all_chunks = []

    for page in pages:
        pieces = _split_into_chunks(page["text"])

        for i, chunk_text in enumerate(pieces):
            if len(chunk_text) < 60:
                continue

            page_title = page.get("page_title") or page.get("page_type", "document").replace("_", " ").title()
            doc_type   = page.get("doc_type", "website_public")

            all_chunks.append({
                "website_id":  website_id,
                "url":         page["url"],
                "page_title":  page_title,
                "page_type":   page.get("page_type", "document"),
                "doc_type":    doc_type,
                "chunk_text":  chunk_text,
                "chunk_index": i,
                "char_count":  len(chunk_text),
                "scraped_at":  scraped_at,
            })

    return all_chunks