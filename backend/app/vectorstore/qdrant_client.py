"""
app/vectorstore/qdrant_client.py
──────────────────────────────────────────────────────────────────────
Provides a shared, lazily-initialized Qdrant client instance.

Why "lazy initialization"?
When FastAPI starts, we don't connect to Qdrant immediately.
We connect on the first actual use. This way, if Qdrant is
temporarily unavailable at startup, FastAPI still starts and
can return health checks — rather than crashing on boot.

Why a shared instance?
Creating a new Qdrant connection for every user request would be
slow (connection handshake overhead) and resource-wasteful (each
connection consumes memory). One shared client handles all requests.
──────────────────────────────────────────────────────────────────────
"""

import logging
from qdrant_client import QdrantClient
from app.config import QDRANT_URL, QDRANT_API_KEY

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client

    if _client is None:
        logger.info("Initializing Qdrant client at %s", QDRANT_URL)
        _client = QdrantClient(
            url     = QDRANT_URL,
            api_key = QDRANT_API_KEY if QDRANT_API_KEY else None,
            timeout = 30,
        )
        logger.info("Qdrant client initialized")

    return _client