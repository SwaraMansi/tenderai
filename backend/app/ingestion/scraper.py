from urllib.parse import urlparse, urljoin
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup
import time

ALLOWED_HOSTS = {"eprocure.gov.in", "bidplus.gem.gov.in", "gem.gov.in"}

def validate_public_tender_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.port not in (None, 443):
        raise ValueError("Only standard-port HTTPS tender URLs are accepted")
    host = parsed.hostname.lower()
    if not any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_HOSTS):
        raise ValueError("URL host is not an approved public procurement domain")
    return url


def fetch_public_page(url: str) -> dict:
    url = validate_public_tender_url(url)
    headers = {"User-Agent": "TenderAI-MVP/1.0 (polite public metadata fetcher)", "Accept": "text/html"}
    last_error = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
                response.raise_for_status()
                final_host = response.url.host.lower()
                if response.url.scheme != "https" or response.url.port not in (None, 443):
                    raise ValueError("Redirected to a non-standard HTTPS endpoint")
                if not any(final_host == allowed or final_host.endswith("." + allowed) for allowed in ALLOWED_HOSTS):
                    raise ValueError("Redirected outside approved procurement domains")
                soup = BeautifulSoup(response.text, "html.parser")
                for node in soup(["script", "style", "noscript"]):
                    node.decompose()
                title = soup.title.get_text(" ", strip=True) if soup.title else ""
                desc = soup.find("meta", attrs={"name": "description"})
                links = []
                for anchor in soup.find_all("a", href=True):
                    href = urljoin(str(response.url), anchor["href"])
                    label = anchor.get_text(" ", strip=True)
                    parsed_link = urlparse(href)
                    link_host = (parsed_link.hostname or "").lower()
                    allowed = any(link_host == host or link_host.endswith("." + host) for host in ALLOWED_HOSTS)
                    tender_like = any(token in (href + " " + label).lower() for token in ("tender", "bid", "nit", "procurement", "notice"))
                    if allowed and parsed_link.scheme == "https" and label and tender_like:
                        links.append({"title": label[:500], "url": href})
                    if len(links) >= 100:
                        break
                return {"source_url": str(response.url), "title": title[:500],
                        "description": desc.get("content", "")[:2000] if desc else "",
                        "page_text": soup.get_text(" ", strip=True)[:20000], "links": links,
                        "source_host": response.url.host, "retrieved_at": datetime.now(timezone.utc).isoformat()}
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status_code = exc.response.status_code
            if status_code != 429 and status_code < 500:
                raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(0.5 * (2 ** attempt))
    if last_error:
        raise last_error
    raise RuntimeError("Public tender page could not be fetched")
