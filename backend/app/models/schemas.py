from pydantic import BaseModel, Field
from typing import List


class ChatRequest(BaseModel):
    message:    str = Field(..., min_length=1, max_length=2000)
    website_id: str = Field(..., description="Routes to correct knowledge collection")
    session_id: str = Field(..., description="Tracks conversation across turns")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message":    "What services do you offer?",
                "website_id": "crushaders_tech",
                "session_id": "sess-1750000000000"
            }
        }
    }


class ChatResponse(BaseModel):
    reply:   str       = Field(..., description="Assistant response text")
    sources: List[str] = Field(default_factory=list,
                               description="Source URLs — empty in Phase 1, populated in Phase 2")

    model_config = {
        "json_schema_extra": {
            "example": {
                "reply":   "Crushaders Tech offers 7 core digital marketing services...",
                "sources": []
            }
        }
    }


class ClearHistoryRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Session ID to clear history for")


class ClearHistoryResponse(BaseModel):
    status:     str = Field(..., example="cleared")
    session_id: str = Field(..., example="sess-1750000000000")


class ChatMessageItem(BaseModel):
    role:      str   = Field(..., description="'user' or 'assistant'")
    content:   str   = Field(..., description="Message text")
    timestamp: float = Field(..., description="UNIX timestamp")


class ChatHistoryResponse(BaseModel):
    session_id: str                   = Field(..., description="The session identifier")
    messages:   List[ChatMessageItem] = Field(default_factory=list, description="Ordered conversation messages")