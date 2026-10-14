"""
app/services/memory_service.py
──────────────────────────────────────────────────────────────────────
Conversational Memory Service.

Manages multi-turn conversation history per session_id:
- Thread-safe in-memory cache backed by data/chat_sessions.json.
- Sliding window mechanism to retain the most recent N turns/messages
  so prompt tokens remain bounded while retaining conversational context.
- Exports history as LangChain BaseMessage objects (HumanMessage, AIMessage)
  for direct injection into LangChain prompt templates.
- Provides session reset/clearing capabilities.
──────────────────────────────────────────────────────────────────────
"""

import os
import json
import time
import logging
import threading
from typing import Any
from datetime import datetime, timezone

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.config import BASE_DIR

logger = logging.getLogger(__name__)

# Maximum messages (user + assistant) to retain per session
MAX_MESSAGES_PER_SESSION: int = 16  # Up to 8 full turns
# Maximum active sessions to store in memory / JSON to prevent unbounded growth
MAX_ACTIVE_SESSIONS: int = 500

_LOCK = threading.Lock()
_SESSIONS_FILE = os.path.join(BASE_DIR, "data", "chat_sessions.json")
_CACHE: dict[str, dict[str, Any]] | None = None


def _load_sessions_unlocked() -> dict[str, dict[str, Any]]:
    """Loads sessions from the JSON file into memory (must be called with _LOCK held)."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    if not os.path.exists(_SESSIONS_FILE):
        _CACHE = {}
        return _CACHE

    try:
        with open(_SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                _CACHE = data
            else:
                _CACHE = {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read chat sessions file (%s); starting fresh cache.", exc)
        _CACHE = {}

    return _CACHE


def _save_sessions_unlocked() -> None:
    """Persists sessions cache to JSON file (must be called with _LOCK held)."""
    global _CACHE
    if _CACHE is None:
        return

    try:
        os.makedirs(os.path.dirname(_SESSIONS_FILE), exist_ok=True)
        # Prune oldest sessions if exceeding MAX_ACTIVE_SESSIONS
        if len(_CACHE) > MAX_ACTIVE_SESSIONS:
            sorted_sessions = sorted(
                _CACHE.items(),
                key=lambda item: item[1].get("updated_at", ""),
                reverse=True
            )
            _CACHE = dict(sorted_sessions[:MAX_ACTIVE_SESSIONS])

        with open(_SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_CACHE, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.warning("Failed to save chat sessions to %s: %s", _SESSIONS_FILE, exc)


def get_history(
    session_id: str,
    limit: int = MAX_MESSAGES_PER_SESSION,
    website_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Returns the list of recent message dicts for a given session_id.
    Each item contains: {"role": "user"|"assistant", "content": str, "timestamp": float}
    """
    if not session_id or not isinstance(session_id, str):
        return []

    with _LOCK:
        sessions = _load_sessions_unlocked()
        session_data = sessions.get(session_id)
        if not session_data or not isinstance(session_data.get("messages"), list):
            return []
        if website_id and session_data.get("website_id") != website_id:
            logger.warning(
                "Ignoring session history from a different tenant | session_id=%s | expected=%s | actual=%s",
                session_id,
                website_id,
                session_data.get("website_id"),
            )
            return []

        messages = session_data["messages"]
        if limit and limit > 0:
            return list(messages[-limit:])
        return list(messages)


def get_langchain_messages(
    session_id: str,
    limit: int = MAX_MESSAGES_PER_SESSION,
    website_id: str | None = None,
) -> list[BaseMessage]:
    """
    Converts session history into LangChain HumanMessage and AIMessage objects
    for inclusion in prompt templates.
    """
    history = get_history(session_id, limit=limit, website_id=website_id)
    lc_messages: list[BaseMessage] = []

    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        if not content:
            continue

        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    return lc_messages


def add_turn(
    session_id: str,
    user_message: str,
    assistant_reply: str,
    website_id: str = "",
) -> None:
    """
    Appends a user message and assistant reply to the session history.
    Enforces maximum message window and updates session metadata.
    """
    if not session_id or not isinstance(session_id, str):
        return

    now_ts = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()

    with _LOCK:
        sessions = _load_sessions_unlocked()
        if session_id not in sessions:
            sessions[session_id] = {
                "session_id": session_id,
                "website_id": website_id or "default",
                "created_at": now_iso,
                "updated_at": now_iso,
                "messages": [],
            }

        session_entry = sessions[session_id]
        # A client-controlled session ID must never carry conversational context
        # from one tenant into another tenant's prompt.
        existing_website_id = session_entry.get("website_id")
        if website_id and existing_website_id and existing_website_id != website_id:
            logger.warning(
                "Resetting session history after tenant change | session_id=%s | old=%s | new=%s",
                session_id,
                existing_website_id,
                website_id,
            )
            session_entry["messages"] = []
        if website_id:
            session_entry["website_id"] = website_id
        session_entry["updated_at"] = now_iso

        messages = session_entry.setdefault("messages", [])

        if user_message and str(user_message).strip():
            messages.append({
                "role": "user",
                "content": str(user_message).strip(),
                "timestamp": now_ts,
            })

        if assistant_reply and str(assistant_reply).strip():
            messages.append({
                "role": "assistant",
                "content": str(assistant_reply).strip(),
                "timestamp": time.time(),
            })

        # Apply sliding window
        if len(messages) > MAX_MESSAGES_PER_SESSION:
            session_entry["messages"] = messages[-MAX_MESSAGES_PER_SESSION:]

        _save_sessions_unlocked()

    logger.debug(
        "Saved turn to session | session_id=%s | total_messages=%d",
        session_id, len(sessions[session_id]["messages"])
    )


def clear_history(session_id: str) -> bool:
    """
    Clears the stored conversation history for a given session_id.
    Returns True if session was found and removed, False otherwise.
    """
    if not session_id:
        return False

    with _LOCK:
        sessions = _load_sessions_unlocked()
        if session_id in sessions:
            del sessions[session_id]
            _save_sessions_unlocked()
            logger.info("Cleared conversation memory for session_id=%s", session_id)
            return True

    return False


def get_session_info(session_id: str) -> dict[str, Any] | None:
    """Returns metadata and messages for a given session."""
    with _LOCK:
        sessions = _load_sessions_unlocked()
        entry = sessions.get(session_id)
        if entry:
            return dict(entry)
    return None
