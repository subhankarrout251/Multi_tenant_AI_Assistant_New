"""
app/services/pipeline/scrape.py
──────────────────────────────────────────────────────────────────────
Reusable scraping + cleaning logic, generalized from scripts/scrape_site.py
to work on a dynamically discovered page list rather than a hardcoded one.
──────────────────────────────────────────────────────────────────────
"""

import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from app.services.pipeline.discover import HEADERS, UnsafeURLError, _safe_get

logger = logging.getLogger(__name__)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["nav", "footer", "header", "script", "style", "noscript", "iframe", "form"]):
        tag.decompose()
    for cls in ["cookie-banner", "popup", "modal", "breadcrumb"]:
        for el in soup.find_all(class_=cls):
            el.decompose()
    return soup.get_text(separator=" ", strip=True)


def _clean_text(text: str) -> str:
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def scrape_pages(pages: list[dict], delay_seconds: float = 1.0) -> list[dict]:
    """
    pages: [{ "url": str, "page_type": str }, ...]
    Returns: [{ "url", "page_type", "text" }, ...] — skips pages that fail
    to fetch or that yield near-empty text (likely non-content pages).
    """
    results = []

    for page in pages:
        url = page["url"]
        try:
            # Revalidate every target and redirect immediately before fetching.
            resp = _safe_get(url, urlparse(url).netloc)
            resp.raise_for_status()
            text = _clean_text(_extract_text(resp.text))

            if len(text) < 100:
                logger.warning("Skipping %s — too little content (%d chars)", url, len(text))
                continue

            results.append({**page, "text": text})
            logger.info("Scraped %s (%d chars)", url, len(text))

        except (requests.RequestException, UnsafeURLError) as e:
            logger.warning("Failed to scrape %s: %s", url, e)

        time.sleep(delay_seconds)  # be polite to the target server

    return results
