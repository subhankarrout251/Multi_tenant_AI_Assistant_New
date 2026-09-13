import logging
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks

from app.models.admin_schemas import OnboardRequest, OnboardAcceptedResponse, OnboardJobStatus
from app.services import job_store
from app.services.onboarding_service import run_onboarding_pipeline
from app.config import ADMIN_API_KEY, ALLOWED_WEBSITE_IDS, WEBSITES_CONFIG_PATH

router = APIRouter()
logger = logging.getLogger(__name__)


def _check_admin_key(x_admin_key: str = Header(default="")) -> None:
    """
    Minimal shared-secret guard for admin endpoints. If ADMIN_API_KEY
    isn't set in the environment, admin routes are open — fine for
    local development, must be set before any real deployment.
    """
    if not ADMIN_API_KEY:
        logger.warning("ADMIN_API_KEY not set — admin endpoints are unprotected")
        return
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key header")


@router.post("/admin/onboard", response_model=OnboardAcceptedResponse, status_code=202)
async def onboard_website(
    request: OnboardRequest,
    background_tasks: BackgroundTasks,
    x_admin_key: str = Header(default=""),
):
    """
    Starts the full automated onboarding pipeline for a new website:
    discover → scrape → chunk → embed → ingest → register.

    Returns immediately with a job_id — the pipeline runs in the
    background. Poll GET /admin/onboard/{job_id} for progress.
    """
    _check_admin_key(x_admin_key)

    if request.website_id in ALLOWED_WEBSITE_IDS:
        logger.info("Re-onboarding existing website_id=%s (will refresh content)", request.website_id)

    job_id = job_store.create_job(request.website_id)

    background_tasks.add_task(
        run_onboarding_pipeline,
        job_id=job_id,
        website_id=request.website_id,
        display_name=request.display_name,
        base_url=request.base_url,
        max_pages=request.max_pages,
    )

    return OnboardAcceptedResponse(job_id=job_id, website_id=request.website_id)


@router.get("/admin/onboard/{job_id}", response_model=OnboardJobStatus)
async def get_onboarding_status(job_id: str, x_admin_key: str = Header(default="")):
    _check_admin_key(x_admin_key)

    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return OnboardJobStatus(**job)


@router.get("/admin/websites")
async def list_websites(x_admin_key: str = Header(default="")):
    _check_admin_key(x_admin_key)

    import json
    try:
        with open(WEBSITES_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"websites": []}