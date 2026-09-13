"""
scripts/ingest_to_qdrant.py
──────────────────────────────────────────────────────────────────────
Loads chunks.json, embeds each chunk using the sentence-transformers
model, and upserts all vectors into the Qdrant collection.

Run after chunk_and_embed.py (and after Qdrant is running):
    python scripts/ingest_to_qdrant.py

This script is idempotent — running it twice won't duplicate data
because we use deterministic UUIDs based on chunk content.
──────────────────────────────────────────────────────────────────────
"""

import os
import json
import uuid
import sys
from tqdm import tqdm
from dotenv import load_dotenv

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams,
    PointStruct,
    PayloadSchemaType,
)

load_dotenv(os.path.join("backend", ".env"))

# ── Config ────────────────────────────────────────────────────────────
WEBSITE_ID       = "crushaders_tech"
CHUNKS_FILE      = os.path.join("data", WEBSITE_ID, "processed", "chunks.json")
QDRANT_URL       = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY   = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME  = "all_websites"
EMBEDDING_MODEL  = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM    = 384
BATCH_SIZE       = 32   # embed 32 chunks at a time (balances speed vs memory)


def make_point_id(website_id: str, url: str, chunk_index: int) -> str:
    """
    Generate a deterministic UUID from the chunk's identity.

    Why deterministic? If you run this script twice, the same chunk
    gets the same UUID. Qdrant's upsert operation updates the existing
    point rather than creating a duplicate. This makes the script safe
    to re-run after website content updates.
    """
    seed = f"{website_id}::{url}::{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def ensure_collection(client: QdrantClient) -> None:
    """
    Create the Qdrant collection if it doesn't exist.
    If it already exists, do nothing.
    """
    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME not in existing:
        print(f"  Creating collection: '{COLLECTION_NAME}'")
        client.create_collection(
            collection_name = COLLECTION_NAME,
            vectors_config  = VectorParams(
                size     = EMBEDDING_DIM,   # must match the embedding model output
                distance = Distance.COSINE  # cosine similarity for text embeddings
            )
        )

        # Index the website_id payload field for fast filtering
        # Without this, every filter query scans ALL vectors — very slow at scale
        client.create_payload_index(
            collection_name = COLLECTION_NAME,
            field_name      = "website_id",
            field_schema    = PayloadSchemaType.KEYWORD
        )

        # Also index page_type for future use (filtering by content type)
        client.create_payload_index(
            collection_name = COLLECTION_NAME,
            field_name      = "page_type",
            field_schema    = PayloadSchemaType.KEYWORD
        )

        print(f"  Collection created with payload indexes on: website_id, page_type")
    else:
        print(f"  Collection '{COLLECTION_NAME}' already exists — will upsert")


def main():
    # ── Load chunks ───────────────────────────────────────────────────
    if not os.path.exists(CHUNKS_FILE):
        print(f"ERROR: {CHUNKS_FILE} not found.")
        print("Run scripts/chunk_and_embed.py first.")
        sys.exit(1)

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"\n{'='*60}")
    print(f"  Ingesting: {WEBSITE_ID}")
    print(f"  Chunks:    {len(chunks)}")
    print(f"  Model:     {EMBEDDING_MODEL}")
    print(f"  Qdrant:    {QDRANT_URL}")
    print(f"{'='*60}\n")

    # ── Load embedding model ──────────────────────────────────────────
    # First run: downloads ~90MB model from HuggingFace and caches it
    # Subsequent runs: loads from cache instantly
    print("  Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"  Model loaded. Output dimension: {model.get_sentence_embedding_dimension()}")

    # ── Connect to Qdrant ─────────────────────────────────────────────
    print(f"\n  Connecting to Qdrant at {QDRANT_URL}...")

    client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY if QDRANT_API_KEY else None,
    timeout=30,
)

    # Quick health check
    try:
        client.get_collections()
        print("  Qdrant connection: OK")
    except Exception as e:
        print(f"  ERROR: Cannot connect to Qdrant: {e}")
        print("  Is Qdrant running? Run: docker start qdrant")
        sys.exit(1)

    # ── Create or verify collection ───────────────────────────────────
    ensure_collection(client)

    # ── Embed and ingest in batches ───────────────────────────────────
    print(f"\n  Embedding and ingesting in batches of {BATCH_SIZE}...")
    total_ingested = 0

    for batch_start in tqdm(range(0, len(chunks), BATCH_SIZE),
                            desc="  Batches", unit="batch"):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]

        # Extract just the text for embedding
        texts = [chunk["chunk_text"] for chunk in batch]

        # Convert texts → vectors
        # show_progress_bar=False because tqdm is already showing progress
        vectors = model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True  # normalize for cosine similarity
        )

        # Build Qdrant PointStruct objects
        points = []
        for chunk, vector in zip(batch, vectors):
            point_id = make_point_id(
                chunk["website_id"],
                chunk["url"],
                chunk["chunk_index"]
            )

            # The payload is everything EXCEPT chunk_text embedded separately
            # We store chunk_text IN the payload so we can retrieve it later
            payload = {
                "website_id":  chunk["website_id"],
                "url":         chunk["url"],
                "page_title":  chunk["page_title"],
                "page_type":   chunk["page_type"],
                "doc_type":    chunk["doc_type"],
                "chunk_text":  chunk["chunk_text"],   # ← critical: store the actual text
                "chunk_index": chunk["chunk_index"],
                "char_count":  chunk["char_count"],
                "scraped_at":  chunk["scraped_at"],
            }

            points.append(PointStruct(
                id      = point_id,
                vector  = vector.tolist(),  # convert numpy array to Python list
                payload = payload
            ))

        # Upsert this batch into Qdrant
        # upsert = insert if new, update if ID already exists
        client.upsert(
            collection_name = COLLECTION_NAME,
            points          = points,
            wait            = True   # wait for indexing to complete before continuing
        )

        total_ingested += len(points)

    print(f"\n{'='*60}")
    print(f"  Ingestion complete!")
    print(f"  Total points ingested: {total_ingested}")
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"  Verify at: {QDRANT_URL}/dashboard")

    # ── Quick verification ────────────────────────────────────────────
    count = client.count(
        collection_name = COLLECTION_NAME,
        count_filter    = None,
        exact           = True
    )
    print(f"  Qdrant reports {count.count} total points in collection.")


if __name__ == "__main__":
    main() 