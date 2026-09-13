"""
app/services/pipeline/ingest.py
──────────────────────────────────────────────────────────────────────
Reusable ingestion logic, generalized from scripts/ingest_to_qdrant.py.
Reuses the same embedding model and Qdrant client already initialized
elsewhere in the app (rag_service, vectorstore) — no duplicate model load.
──────────────────────────────────────────────────────────────────────
"""

import uuid
import logging
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, PayloadSchemaType
)

from app.config import QDRANT_COLLECTION, EMBEDDING_DIM
from app.vectorstore.qdrant_client import get_qdrant_client
from app.services.rag_service import get_embedding_model

logger = logging.getLogger(__name__)

BATCH_SIZE = 32


def _make_point_id(website_id: str, url: str, chunk_index: int) -> str:
    seed = f"{website_id}::{url}::{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _ensure_collection(client) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION in existing:
        return

    logger.info("Creating collection: '%s'", QDRANT_COLLECTION)
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=QDRANT_COLLECTION, field_name="website_id",
        field_schema=PayloadSchemaType.KEYWORD
    )
    client.create_payload_index(
        collection_name=QDRANT_COLLECTION, field_name="page_type",
        field_schema=PayloadSchemaType.KEYWORD
    )


def ingest_chunks(chunks: list[dict]) -> int:
    """
    Embeds and upserts chunk records into Qdrant.
    Idempotent — deterministic point IDs mean re-onboarding the same
    website updates existing points rather than duplicating them.
    Returns the number of points ingested.
    """
    if not chunks:
        return 0

    client = get_qdrant_client()
    _ensure_collection(client)

    model = get_embedding_model()
    total = 0

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start: batch_start + BATCH_SIZE]
        texts = [c["chunk_text"] for c in batch]
        vectors = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

        points = []
        for chunk, vector in zip(batch, vectors):
            point_id = _make_point_id(chunk["website_id"], chunk["url"], chunk["chunk_index"])
            points.append(PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload={k: v for k, v in chunk.items()}
            ))

        client.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)
        total += len(points)

    logger.info("Ingested %d points into '%s'", total, QDRANT_COLLECTION)
    return total