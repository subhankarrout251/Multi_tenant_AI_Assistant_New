from pydantic import BaseModel, Field
from typing import Optional


class AdminLoginRequest(BaseModel):
    api_key: str = Field(..., min_length=1, max_length=500)


class OnboardRequest(BaseModel):
    website_id: str = Field(
        ..., pattern=r"^[a-z0-9_]+$",
        description="Slug identifier, e.g. 'hotel_chain_bhubaneswar'"
    )
    display_name: str = Field(..., min_length=1, max_length=200)
    base_url: str = Field(..., description="Homepage URL of the site to onboard")
    max_pages: int = Field(default=40, ge=1, le=200)

    model_config = {
        "json_schema_extra": {
            "example": {
                "website_id": "hotel_chain_bbsr",
                "display_name": "Hotel Chain Bhubaneswar",
                "base_url": "https://example-hotel.com",
                "max_pages": 40
            }
        }
    }


class OnboardAcceptedResponse(BaseModel):
    job_id: str
    website_id: str
    status: str = "queued"


class OnboardJobStatus(BaseModel):
    job_id: str
    website_id: str
    status: str
    pages_discovered: int
    pages_scraped: int
    chunks_created: int
    points_ingested: int
    error: Optional[str] = None
    created_at: str
    updated_at: str
