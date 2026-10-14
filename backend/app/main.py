import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat
from app.config import APP_ENV, ALLOWED_ORIGINS
from app.routers import chat, admin

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup: pre-load the embedding model and verify Qdrant.
    Pre-loading means the first user request doesn't incur the
    model-loading delay — it's already in memory.
    """
    logger.info("Starting up Crushaders Tech Chatbot API...")

    # Pre-load embedding model into memory
    from app.services.rag_service import get_embedding_model
    get_embedding_model()
    logger.info("Embedding model pre-loaded")

   # Verify Qdrant is reachable
    from app.vectorstore.qdrant_client import get_qdrant_client
    try:
        client = get_qdrant_client()
        collections = [c.name for c in client.get_collections().collections]
        logger.info("Qdrant connected. Collections: %s", collections)
    except Exception as e:
        logger.error("Qdrant connection failed: %s", e)
        logger.warning("Chatbot will start but RAG will fail until Qdrant is reachable")

    logger.info("Startup complete. API is ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title       = "Crushaders Tech Chatbot API",
    description = "Phase 2 — RAG pipeline with Qdrant and Groq LLM",
    version     = "2.0.0",
    docs_url    = "/docs" if APP_ENV == "development" else None,
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["POST", "GET", "OPTIONS", "DELETE"],
    allow_headers     = ["Content-Type", "Authorization", "X-Admin-Key"],
)

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "phase": "2-rag", "env": APP_ENV}