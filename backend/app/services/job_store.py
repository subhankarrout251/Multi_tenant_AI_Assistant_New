"""
app/services/job_store.py
──────────────────────────────────────────────────────────────────────
Tracks onboarding job status so a caller can poll progress.

Deliberately simple: an in-memory dict backed by a JSON file for
persistence across restarts. This is the natural table to become
`onboarding_jobs` once PostgreSQL is added — the interface below
(create_job / update_job / get_job) is the contract to preserve
when that migration happens.
──────────────────────────────────────────────────────────────────────
"""

import os
import json
import uuid
import threading
from datetime import datetime, timezone

_LOCK = threading.Lock()
_JOBS_FILE = os.path.join("..", "data", "onboarding_jobs.json")


def _load() -> dict:
    if not os.path.exists(_JOBS_FILE):
        return {}
    try:
        with open(_JOBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save(jobs: dict) -> None:
    os.makedirs(os.path.dirname(_JOBS_FILE), exist_ok=True)
    with open(_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)


def create_job(website_id: str) -> str:
    job_id = str(uuid.uuid4())
    with _LOCK:
        jobs = _load()
        jobs[job_id] = {
            "job_id": job_id,
            "website_id": website_id,
            "status": "queued",
            "pages_discovered": 0,
            "pages_scraped": 0,
            "chunks_created": 0,
            "points_ingested": 0,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _save(jobs)
    return job_id


def update_job(job_id: str, **fields) -> None:
    with _LOCK:
        jobs = _load()
        if job_id not in jobs:
            return
        jobs[job_id].update(fields)
        jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save(jobs)


def get_job(job_id: str) -> dict | None:
    with _LOCK:
        return _load().get(job_id)


def list_jobs() -> list[dict]:
    with _LOCK:
        return list(_load().values())