import os
import logging
import re
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks, Form, UploadFile, File, Query
from fastapi.responses import FileResponse

from app.models.admin_schemas import OnboardRequest, OnboardAcceptedResponse, OnboardJobStatus
from app.services import job_store
from app.services.onboarding_service import (
    run_onboarding_pipeline,
    run_pdf_onboarding_pipeline,
    run_document_onboarding_pipeline,
    register_website,
)
from app.services.finetune_service import generate_finetune_dataset_task
from app.config import ADMIN_API_KEY, ALLOWED_WEBSITE_IDS, WEBSITES_CONFIG_PATH, BASE_DIR

router = APIRouter()
logger = logging.getLogger(__name__)
_WEBSITE_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


def _validate_website_id(website_id: str) -> str:
    """Keep tenant IDs safe when they are used to form data-directory paths."""
    if not isinstance(website_id, str) or not _WEBSITE_ID_PATTERN.fullmatch(website_id):
        raise HTTPException(
            status_code=400,
            detail="website_id must contain only lowercase letters, numbers, and underscores",
        )
    return website_id


def _safe_upload_filename(filename: str | None) -> str:
    """Reject path components rather than allowing an upload to escape its tenant directory."""
    safe_filename = os.path.basename(filename or "")
    if not safe_filename or safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid upload filename")
    return safe_filename


def _check_admin_key(x_admin_key: str = Header(default="")) -> None:
    """
    Minimal shared-secret guard for admin endpoints. If ADMIN_API_KEY
    isn't set in the environment, admin routes are open — fine for
    local development, must be set before any real deployment.
    """
    if not ADMIN_API_KEY:
        logger.warning("ADMIN_API_KEY not set — admin endpoints are unprotected")
        return
    if x_admin_key.strip() != ADMIN_API_KEY.strip():
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


@router.post("/admin/setup", response_model=OnboardAcceptedResponse, status_code=202)
async def setup_client(
    background_tasks: BackgroundTasks,
    website_id: str = Form(..., description="Unique client identifier, e.g. 'grand_hotel'"),
    display_name: str = Form(..., description="Display name, e.g. 'Grand Palace Hotel'"),
    website_url: str = Form(default="", description="Hotel / Company website URL"),
    phone: str = Form(default="", description="Contact phone number"),
    email: str = Form(default="", description="Contact email address"),
    address: str = Form(default="", description="Physical location / address"),
    files: list[UploadFile] = File(default=[], description="PDF (.pdf) or Word (.docx) documents"),
    x_admin_key: str = Header(default=""),
):
    """
    Unified setup endpoint: configure hotel/company name, URL, contact info,
    and documents (.pdf, .docx) all in ONE place.
    Updates backend, Qdrant vectors, and sets this client active immediately.
    """
    _check_admin_key(x_admin_key)
    _validate_website_id(website_id)

    upload_dir = os.path.join(BASE_DIR, "data", website_id, "docs")
    os.makedirs(upload_dir, exist_ok=True)

    saved_paths = []
    allowed_exts = (".pdf", ".docx")

    for file in files:
        if file.filename:
            filename = _safe_upload_filename(file.filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext not in allowed_exts:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}' is not supported. Please upload PDF (.pdf) or Word (.docx) files only."
                )
            dest_path = os.path.join(upload_dir, filename)
            content = await file.read()
            with open(dest_path, "wb") as f:
                f.write(content)
            saved_paths.append(dest_path)

    contact_info = {
        "phone": phone.strip(),
        "email": email.strip(),
        "address": address.strip(),
    }

    job_id = job_store.create_job(website_id)

    # If no new files were uploaded, update client profile details immediately
    if not saved_paths:
        register_website(
            website_id=website_id,
            display_name=display_name,
            base_url=website_url.strip(),
            contact=contact_info,
            set_as_active=True,
        )
        job_store.update_job(job_id, status="completed", points_ingested=0)
        return OnboardAcceptedResponse(job_id=job_id, website_id=website_id)

    background_tasks.add_task(
        run_document_onboarding_pipeline,
        job_id=job_id,
        website_id=website_id,
        display_name=display_name,
        doc_paths=saved_paths,
        base_url=website_url.strip(),
        contact=contact_info,
    )

    return OnboardAcceptedResponse(job_id=job_id, website_id=website_id)


@router.post("/admin/onboard/pdf", response_model=OnboardAcceptedResponse, status_code=202)
async def onboard_pdf_documents(
    background_tasks: BackgroundTasks,
    website_id: str = Form(..., description="Unique client identifier, e.g. 'grand_hotel'"),
    display_name: str = Form(..., description="Human-readable business name, e.g. 'Grand Palace Hotel'"),
    files: list[UploadFile] = File(..., description="One or more PDF or DOCX documents to ingest"),
    x_admin_key: str = Header(default=""),
):
    """
    Onboards a new client or adds knowledge using uploaded PDF/DOCX files.
    """
    _check_admin_key(x_admin_key)
    _validate_website_id(website_id)
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Store uploaded documents in data/{website_id}/docs/
    upload_dir = os.path.join(BASE_DIR, "data", website_id, "docs")
    os.makedirs(upload_dir, exist_ok=True)

    saved_paths = []
    allowed_exts = (".pdf", ".docx")

    for file in files:
        filename = _safe_upload_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail=f"File '{file.filename}' is not a PDF or DOCX file")

        dest_path = os.path.join(upload_dir, filename)
        content = await file.read()
        with open(dest_path, "wb") as f:
            f.write(content)
        saved_paths.append(dest_path)

    job_id = job_store.create_job(website_id)

    background_tasks.add_task(
        run_document_onboarding_pipeline,
        job_id=job_id,
        website_id=website_id,
        display_name=display_name,
        doc_paths=saved_paths,
    )

    return OnboardAcceptedResponse(job_id=job_id, website_id=website_id)


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


@router.post("/admin/websites/active")
async def set_active_website(
    payload: dict,
    x_admin_key: str = Header(default="")
):
    """Sets which company/hotel is currently active for the chatbot."""
    _check_admin_key(x_admin_key)
    website_id = payload.get("website_id")
    _validate_website_id(website_id)

    try:
        with open(WEBSITES_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"websites": []}

    sites = data.get("websites", [])
    if not any(site.get("website_id") == website_id for site in sites):
        raise HTTPException(status_code=404, detail=f"Unknown website_id '{website_id}'")

    data["active_id"] = website_id
    with open(WEBSITES_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return {"status": "ok", "active_id": website_id}


@router.get("/admin/websites/{website_id}/docs")
async def list_client_documents(website_id: str, x_admin_key: str = Header(default="")):
    """Lists all uploaded PDF and DOCX files for a given client."""
    _check_admin_key(x_admin_key)
    _validate_website_id(website_id)
    docs_dir = os.path.join(BASE_DIR, "data", website_id, "docs")
    if not os.path.isdir(docs_dir):
        return {"website_id": website_id, "documents": []}

    docs = []
    from datetime import datetime
    for fname in sorted(os.listdir(docs_dir)):
        if fname.startswith("."):
            continue
        fpath = os.path.join(docs_dir, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            docs.append({
                "filename": fname,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "doc_type": "pdf" if fname.lower().endswith(".pdf") else "docx",
            })
    return {"website_id": website_id, "documents": docs}


@router.delete("/admin/websites/{website_id}/docs/{filename}")
async def delete_client_document(website_id: str, filename: str, x_admin_key: str = Header(default="")):
    """Deletes an uploaded document file from disk."""
    _check_admin_key(x_admin_key)
    _validate_website_id(website_id)
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    fpath = os.path.join(BASE_DIR, "data", website_id, "docs", safe_filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Document '{safe_filename}' not found")
    try:
        os.remove(fpath)
        return {"status": "ok", "message": f"Deleted {safe_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {e}")


@router.put("/admin/websites/{website_id}")
async def update_client_profile(
    website_id: str,
    payload: dict,
    x_admin_key: str = Header(default="")
):
    """Directly updates client profile info (display_name, base_url, contact) in websites.json."""
    _check_admin_key(x_admin_key)
    _validate_website_id(website_id)
    display_name = payload.get("display_name", website_id)
    base_url = payload.get("base_url", "")
    contact = payload.get("contact", {})

    register_website(
        website_id=website_id,
        display_name=display_name,
        base_url=base_url,
        contact=contact,
        set_as_active=payload.get("set_as_active", False)
    )
    return {"status": "ok", "message": f"Updated profile for {website_id}"}


@router.post("/admin/finetune/generate", response_model=OnboardAcceptedResponse, status_code=202)
async def generate_finetune_dataset(
    background_tasks: BackgroundTasks,
    website_id: str = Form(..., description="Website/Company ID to generate dataset for"),
    max_chunks: int = Form(default=40, description="Max number of chunks to generate from"),
    x_admin_key: str = Header(default=""),
):
    """
    Generates a Chat JSONL fine-tuning dataset from the company's ingested knowledge chunks.
    Runs in the background. Poll GET /admin/onboard/{job_id} for completion.
    """
    _check_admin_key(x_admin_key)
    _validate_website_id(website_id)
    job_id = job_store.create_job(website_id)
    background_tasks.add_task(
        generate_finetune_dataset_task,
        job_id=job_id,
        website_id=website_id,
        max_chunks=max_chunks,
    )
    return OnboardAcceptedResponse(job_id=job_id, website_id=website_id)


@router.post("/admin/finetune/upload", status_code=200)
async def upload_finetune_dataset(
    website_id: str = Form(..., description="Website/Company ID"),
    file: UploadFile = File(..., description="Prepared .jsonl fine-tuning dataset"),
    x_admin_key: str = Header(default=""),
):
    """
    Uploads a pre-prepared .jsonl fine-tuning dataset file directly for a company.
    """
    _check_admin_key(x_admin_key)
    _validate_website_id(website_id)
    if not (file.filename or "").lower().endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="Only .jsonl format is accepted for fine-tuning datasets.")

    dest_dir = os.path.join(BASE_DIR, "data", website_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, "finetune_data.jsonl")

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    return {"status": "ok", "message": f"Dataset saved to data/{website_id}/finetune_data.jsonl", "bytes": len(content)}


@router.get("/admin/finetune/{website_id}")
async def get_finetune_dataset(
    website_id: str,
    x_admin_key: str = Header(default=""),
    admin_key: str = Query(default=""),
):
    """
    Downloads the generated or uploaded fine-tuning .jsonl dataset for this company.
    """
    key = x_admin_key or admin_key
    _check_admin_key(key)
    _validate_website_id(website_id)
    file_path = os.path.join(BASE_DIR, "data", website_id, "finetune_data.jsonl")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"No fine-tuning dataset found for '{website_id}'")
    return FileResponse(file_path, media_type="application/jsonl", filename=f"{website_id}_finetune.jsonl")
