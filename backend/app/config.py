import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────
APP_ENV: str = os.getenv("APP_ENV", "development")

ALLOWED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if origin.strip()
]

# ── Dynamic website registry ──────────────────────────────────────────
# Base directory of the repository
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEBSITES_CONFIG_PATH = os.getenv(
    "WEBSITES_CONFIG_PATH",
    os.path.join(BASE_DIR, "data", "websites.json")
)


def load_allowed_website_ids() -> list[str]:
    """
    Read the list of active website_ids from data/websites.json.

    This is called at startup AND can be called again at runtime
    (e.g. from an admin endpoint) to pick up newly onboarded clients
    without restarting the server.

    Falls back to a safe default if the file is missing or malformed —
    we never want a bad config file to crash the whole API.
    """
    try:
        with open(WEBSITES_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        active_ids = [
            site["website_id"]
            for site in data.get("websites", [])
            if site.get("active", False)
        ]

        if not active_ids:
            logger.warning(
                "No active websites found in %s — falling back to default",
                WEBSITES_CONFIG_PATH
            )
            return ["crushaders_tech"]

        logger.info("Loaded %d active website(s): %s", len(active_ids), active_ids)
        return active_ids

    except FileNotFoundError:
        logger.warning(
            "%s not found — falling back to default website list",
            WEBSITES_CONFIG_PATH
        )
        return ["crushaders_tech"]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse %s: %s — falling back to default", WEBSITES_CONFIG_PATH, e)
        return ["crushaders_tech"]


def get_active_website_info(website_id: str = None) -> dict:
    """Retrieve metadata (display_name, base_url, contact) for website_id or the default active site."""
    default_fallback = {
        "website_id": "crushaders_tech",
        "display_name": "Crushaders Tech Solutions",
        "base_url": "https://crushaderstech.com",
        "active": True,
        "contact": {
            "email": "sales@crushaderstech.com",
            "phone": "+91 7077479235",
            "address": "GPS Tower, Patia, Bhubaneswar – 751031, Odisha",
        }
    }
    try:
        with open(WEBSITES_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        sites = data.get("websites", [])
        if not sites:
            return default_fallback

        target_id = website_id or data.get("active_id")

        if target_id:
            for site in sites:
                if site.get("website_id") == target_id:
                    res = dict(site)
                    if "contact" not in res or not res["contact"]:
                        res["contact"] = default_fallback["contact"]
                    return res

        for site in sites:
            if site.get("active", False):
                res = dict(site)
                if "contact" not in res or not res["contact"]:
                    res["contact"] = default_fallback["contact"]
                return res

        return sites[0]
    except Exception:
        return default_fallback


def get_website_info(website_id: str) -> dict:
    return get_active_website_info(website_id)


# Loaded once at import time (module load = app startup)
ALLOWED_WEBSITE_IDS: list[str] = load_allowed_website_ids()

# ── Contact ───────────────────────────────────────────────────────────
CONTACT: dict[str, str] = {
    "email":   "sales@crushaderstech.com",
    "phone":   "+91 7077479235",
    "india":   "GPS Tower, Patia, Bhubaneswar – 751031, Odisha",
    "usa":     "6914 W Harrison St, Chandler, AZ",
    "uk":      "70-74 Brunswick St, Stockton-On-Tees",
}

# ── Qdrant ────────────────────────────────────────────────────────────
QDRANT_URL: str        = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY: str    = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION: str = "all_websites"
# ── Embedding Model ───────────────────────────────────────────────────
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM:   int = 384
TOP_K_CHUNKS:    int = 4

# ── Hybrid routing thresholds ─────────────────────────────────────────
# Above this score → confident match, use RAG straightforwardly
RAG_CONFIDENCE_HIGH: float = 0.55
# Below this score → not company-related, use general LLM only
RAG_CONFIDENCE_LOW:  float = 0.35
# Between the two → use RAG context but let the LLM supplement
# with general knowledge if needed (handled via prompt instructions)

# ── Groq LLM ──────────────────────────────────────────────────────────
GROQ_API_KEY: str      = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str        = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE: float = 0.2
LLM_MAX_RETRIES: int   = 1   # retry once on rate limit / transient failure

# ── Chunking (shared between manual scripts and onboarding pipeline) ─
CHUNK_SIZE:    int = 450
CHUNK_OVERLAP: int = 80

# ── Onboarding automation ─────────────────────────────────────────────
ONBOARD_MAX_PAGES: int = int(os.getenv("ONBOARD_MAX_PAGES", "40"))
ADMIN_API_KEY:      str = os.getenv("ADMIN_API_KEY", "").strip()