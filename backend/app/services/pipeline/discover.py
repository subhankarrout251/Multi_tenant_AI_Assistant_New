"""
app/services/pipeline/discover.py
──────────────────────────────────────────────────────────────────────
Discovers a website's pages automatically — no hardcoded page list.

Strategy:
  1. Try {base_url}/sitemap.xml first (handles simple sitemaps and
     one level of sitemap-index nesting).
  2. If no usable sitemap, fall back to crawling internal links
     starting from the homepage (breadth-first, same-domain only).

Includes a basic SSRF guard — onboarding accepts an arbitrary URL
from the caller, so we refuse to crawl private/loopback IPs.
──────────────────────────────────────────────────────────────────────
"""

import socket
import ipaddress
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip",
    ".css", ".js", ".ico", ".xml", ".mp4", ".mp3", ".doc", ".docx"
)


class UnsafeURLError(Exception):
    """Raised when a target URL resolves to a private/loopback address."""
    pass


def assert_public_url(url: str) -> None:
    """
    Minimal SSRF guard. Onboarding accepts a URL from whoever calls the
    admin endpoint — refuse anything that resolves to a private,
    loopback, or link-local address so this can't be used to probe
    internal infrastructure.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeURLError(f"Could not parse hostname from {url}")

    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)}
    except socket.gaierror as e:
        raise UnsafeURLError(f"Could not resolve host {parsed.hostname}: {e}") from e

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_reserved, ip.is_multicast, ip.is_unspecified)):
            raise UnsafeURLError(f"Refusing to crawl private/internal address: {parsed.hostname} → {ip}")


def _safe_get(url: str, allowed_domain: str | None = None) -> requests.Response:
    """Fetch only public HTTP(S) URLs, checking every redirect target."""
    current_url = url
    for _ in range(6):
        assert_public_url(current_url)
        if allowed_domain and urlparse(current_url).netloc != allowed_domain:
            raise UnsafeURLError(f"Refusing cross-domain URL: {current_url}")
        response = requests.get(current_url, headers=HEADERS, timeout=10, allow_redirects=False)
        if not response.is_redirect:
            return response
        location = response.headers.get("location")
        if not location:
            return response
        current_url = urljoin(current_url, location)
    raise UnsafeURLError("Too many redirects while crawling")


def infer_page_type(url: str) -> str:
    """Best-effort page_type classification from the URL path alone."""
    path = urlparse(url).path.lower()

    if path in ("", "/"):
        return "home"
    if "about" in path:
        return "about"
    if "contact" in path:
        return "contact"
    if "blog" in path or "news" in path:
        return "blog"
    if any(k in path for k in ["service", "solution", "product"]):
        return "service"
    if any(k in path for k in ["industr", "sector", "vertical"]):
        return "industry"
    if "faq" in path:
        return "faq"
    return "general"


def _try_sitemap(base_url: str, max_pages: int) -> list[str]:
    """Attempt to read sitemap.xml (and one level of nested sitemaps)."""
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    try:
        resp = _safe_get(sitemap_url, urlparse(base_url).netloc)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "xml")
    urls = [loc.get_text(strip=True) for loc in soup.find_all("loc")]

    if soup.find("sitemapindex"):
        nested_urls = []
        for nested_sitemap in urls[:5]:
            try:
                nested_resp = _safe_get(nested_sitemap, urlparse(base_url).netloc)
                nested_resp.raise_for_status()
                nested_soup = BeautifulSoup(nested_resp.text, "xml")
                nested_urls.extend(
                    loc.get_text(strip=True) for loc in nested_soup.find_all("loc")
                )
            except (requests.RequestException, UnsafeURLError):
                continue
            if len(nested_urls) >= max_pages:
                break
        return nested_urls[:max_pages]

    return urls[:max_pages]


def _crawl_from_homepage(base_url: str, max_pages: int) -> list[str]:
    """Fallback: breadth-first crawl of same-domain internal links."""
    domain = urlparse(base_url).netloc
    seen = {base_url}
    queue = [base_url]
    discovered = []

    while queue and len(discovered) < max_pages:
        url = queue.pop(0)
        try:
            resp = _safe_get(url, domain)
            resp.raise_for_status()
        except (requests.RequestException, UnsafeURLError):
            continue

        discovered.append(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"]).split("#")[0]
            if urlparse(href).netloc != domain:
                continue
            if href.lower().endswith(SKIP_EXTENSIONS):
                continue
            if href not in seen:
                seen.add(href)
                queue.append(href)

    return discovered[:max_pages]


def discover_pages(base_url: str, max_pages: int = 40) -> list[dict]:
    """
    Returns a list of { "url": str, "page_type": str } dicts.
    Tries sitemap.xml first; falls back to crawling internal links.
    """
    assert_public_url(base_url)

    urls = _try_sitemap(base_url, max_pages)
    domain = urlparse(base_url).netloc
    urls = [url for url in urls if urlparse(url).netloc == domain and _is_safe_discovered_url(url)]
    source = "sitemap"

    if not urls:
        urls = _crawl_from_homepage(base_url, max_pages)
        source = "crawl"

    logger.info("Discovered %d pages for %s via %s", len(urls), base_url, source)

    return [{"url": u, "page_type": infer_page_type(u)} for u in urls]


def _is_safe_discovered_url(url: str) -> bool:
    try:
        assert_public_url(url)
        return True
    except UnsafeURLError:
        logger.warning("Ignoring unsafe URL discovered in sitemap: %s", url)
        return False
