import logging
from fastapi import APIRouter, HTTPException
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


@router.post("/chat", response_model=ChatResponse, summary="Send a message to the chatbot")
async def chat(request: ChatRequest) -> ChatResponse:
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

    result = await handle_message(
        message=request.message,
        website_id=request.website_id,
        session_id=request.session_id,
    )

    return ChatResponse(reply=result["reply"], sources=result["sources"])


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse, summary="Get conversation history")
async def get_chat_history(session_id: str) -> ChatHistoryResponse:
    """Returns the message history for a given session."""
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
async def clear_chat(request: ClearHistoryRequest) -> ClearHistoryResponse:
    """Clears conversation memory for the provided session_id."""
    clear_session_memory(request.session_id)
    return ClearHistoryResponse(status="cleared", session_id=request.session_id)


@router.delete("/chat/history/{session_id}", response_model=ClearHistoryResponse, summary="Delete conversation memory")
async def delete_chat_history(session_id: str) -> ClearHistoryResponse:
    """Deletes conversation memory for the provided session_id."""
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
