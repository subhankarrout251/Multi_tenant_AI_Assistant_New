"""
app/vectorstore/qdrant_client.py
──────────────────────────────────────────────────────────────────────
Provides a shared, lazily-initialized Qdrant client instance.

Attempts to connect to remote Qdrant (via QDRANT_URL, e.g. Docker or Cloud).
If remote Qdrant is unreachable or not running, seamlessly falls back to
local embedded persistent Qdrant storage at data/qdrant_storage.

This prevents '[Errno 61] Connection refused' crashes when Docker or
an external Qdrant service is not running locally.
──────────────────────────────────────────────────────────────────────
"""

import os
import logging
from qdrant_client import QdrantClient
from app.config import QDRANT_URL, QDRANT_API_KEY, BASE_DIR

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client

    if _client is None:
        client_connected = False
        if QDRANT_URL:
            try:
                candidate = QdrantClient(
                    url     = QDRANT_URL,
                    api_key = QDRANT_API_KEY if QDRANT_API_KEY else None,
                    timeout = 3,
                )
                # Verify server is responding
                candidate.get_collections()
                _client = candidate
                client_connected = True
                logger.info("Connected to remote Qdrant server at %s", QDRANT_URL)
            except Exception as e:
                logger.warning(
                    "Remote Qdrant at %s unreachable (%s). Using local embedded Qdrant database.",
                    QDRANT_URL, e
                )

        if not client_connected:
            storage_path = os.path.join(BASE_DIR, "data", "qdrant_storage")
            os.makedirs(storage_path, exist_ok=True)
            _client = QdrantClient(path=storage_path)
            logger.info("Initialized local persistent Qdrant database at '%s'", storage_path)

    return _client