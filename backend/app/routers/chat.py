import logging
import secrets
from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ClearHistoryRequest,
    ClearHistoryResponse,
    ChatHistoryResponse,
    ChatMessageItem,
)
from app.services.chat_service import handle_message
from app.services.memory_service import get_history, clear_history as clear_session_memory
from app.config import load_allowed_website_ids

router = APIRouter()
logger = logging.getLogger(__name__)


def _owned_session_id(request: Request) -> str:
    """Return the chat ID bound to this signed browser session, creating one if needed."""
    session_id = request.session.get("chat_session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = f"sess-{secrets.token_urlsafe(24)}"
        request.session["chat_session_id"] = session_id
    return session_id


def _require_session_owner(request: Request, session_id: str) -> None:
    if not secrets.compare_digest(_owned_session_id(request), session_id):
        raise HTTPException(status_code=403, detail="This chat session is not owned by the current browser session")


@router.post("/chat", response_model=ChatResponse, summary="Send a message to the chatbot")
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """
    Main chat endpoint.

    Validates the website_id against the dynamic whitelist, then delegates
    to chat_service for response generation with conversation memory.
    """
    allowed_ids = load_allowed_website_ids()
    if request.website_id not in allowed_ids:
        logger.warning("Rejected unknown website_id: %s", request.website_id)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown website_id '{request.website_id}'. "
                   f"Allowed: {allowed_ids}"
        )

    session_id = _owned_session_id(http_request)
    result = await handle_message(
        message=request.message,
        website_id=request.website_id,
        session_id=session_id,
    )

    return ChatResponse(reply=result["reply"], sources=result["sources"], session_id=session_id)


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse, summary="Get conversation history")
async def get_chat_history(session_id: str, request: Request) -> ChatHistoryResponse:
    """Returns the message history for a given session."""
    _require_session_owner(request, session_id)
    messages = get_history(session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            ChatMessageItem(
                role=m["role"],
                content=m["content"],
                timestamp=m.get("timestamp", 0.0),
            )
            for m in messages
        ],
    )


@router.post("/chat/clear", response_model=ClearHistoryResponse, summary="Clear conversation memory")
async def clear_chat(request: ClearHistoryRequest, http_request: Request) -> ClearHistoryResponse:
    """Clears conversation memory for the provided session_id."""
    _require_session_owner(http_request, request.session_id)
    clear_session_memory(request.session_id)
    return ClearHistoryResponse(status="cleared", session_id=request.session_id)


@router.delete("/chat/history/{session_id}", response_model=ClearHistoryResponse, summary="Delete conversation memory")
async def delete_chat_history(session_id: str, request: Request) -> ClearHistoryResponse:
    """Deletes conversation memory for the provided session_id."""
    _require_session_owner(request, session_id)
    clear_session_memory(session_id)
    return ClearHistoryResponse(status="cleared", session_id=session_id)


@router.get("/info", summary="Get active company / hotel profile")
async def get_info(website_id: str = None) -> dict:
    """
    Returns public metadata (display name, website_id, base_url, contact info)
    for the requested website_id or for the current active/default client.
    """
    from app.config import get_active_website_info
    return get_active_website_info(website_id)
