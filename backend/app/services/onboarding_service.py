"""
app/services/onboarding_service.py
──────────────────────────────────────────────────────────────────────
Orchestrates the full automated onboarding pipeline for a new website:

  discover pages → scrape → chunk → embed & ingest → register in
  data/websites.json → mark job complete

This replaces manually running scrape_site.py, chunk_and_embed.py,
and ingest_to_qdrant.py by hand for each new client.

Runs synchronously inside a background thread (see admin.py router) —
scraping and embedding are blocking operations, so this must never run
on the FastAPI event loop directly.
──────────────────────────────────────────────────────────────────────
"""

import os
import json
import logging
import threading

from app.services.pipeline.discover import discover_pages, UnsafeURLError
from app.services.pipeline.scrape import scrape_pages
from app.services.pipeline.chunk import chunk_pages
from app.services.pipeline.ingest import ingest_chunks
from app.services import job_store
from app.config import WEBSITES_CONFIG_PATH, ONBOARD_MAX_PAGES, load_allowed_website_ids
import app.config as config

logger = logging.getLogger(__name__)
_WEBSITES_FILE_LOCK = threading.Lock()


def _register_website(website_id: str, display_name: str, base_url: str) -> None:
    """Adds (or updates) an entry in data/websites.json and refreshes
    the in-memory allowlist so the new client can chat immediately —
    no server restart required."""
    from datetime import date

    with _WEBSITES_FILE_LOCK:
        try:
            with open(WEBSITES_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"websites": []}

        sites = data.setdefault("websites", [])
        existing = next((s for s in sites if s["website_id"] == website_id), None)

        entry = {
            "website_id": website_id,
            "display_name": display_name,
            "base_url": base_url,
            "active": True,
            "onboarded_at": date.today().isoformat(),
        }

        if existing:
            existing.update(entry)
        else:
            sites.append(entry)

        os.makedirs(os.path.dirname(WEBSITES_CONFIG_PATH), exist_ok=True)
        with open(WEBSITES_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    config.ALLOWED_WEBSITE_IDS = load_allowed_website_ids()
    logger.info("Registered website_id=%s — allowlist refreshed", website_id)


def run_onboarding_pipeline(
    job_id: str,
    website_id: str,
    display_name: str,
    base_url: str,
    max_pages: int = ONBOARD_MAX_PAGES,
) -> None:
    """
    The full pipeline, run synchronously. Called from a background
    thread by the admin router — never called directly on the request
    thread.
    """
    try:
        job_store.update_job(job_id, status="discovering")
        pages = discover_pages(base_url, max_pages=max_pages)
        job_store.update_job(job_id, pages_discovered=len(pages))

        if not pages:
            raise RuntimeError("No pages discovered — check the base_url is reachable")

        job_store.update_job(job_id, status="scraping")
        scraped = scrape_pages(pages)
        job_store.update_job(job_id, pages_scraped=len(scraped))

        if not scraped:
            raise RuntimeError("No pages could be scraped successfully")

        job_store.update_job(job_id, status="chunking")
        chunks = chunk_pages(website_id, scraped)
        job_store.update_job(job_id, chunks_created=len(chunks))

        job_store.update_job(job_id, status="embedding_ingesting")
        ingested = ingest_chunks(chunks)
        job_store.update_job(job_id, points_ingested=ingested)

        job_store.update_job(job_id, status="registering")
        _register_website(website_id, display_name, base_url)

        job_store.update_job(job_id, status="completed")
        logger.info("Onboarding complete | website_id=%s | job_id=%s", website_id, job_id)

    except UnsafeURLError as e:
        logger.error("Onboarding rejected (unsafe URL) | job_id=%s | %s", job_id, e)
        job_store.update_job(job_id, status="failed", error=str(e))

    except Exception as e:
        logger.exception("Onboarding failed | job_id=%s", job_id)
        job_store.update_job(job_id, status="failed", error=str(e))