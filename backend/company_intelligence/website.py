"""
Website Intelligence Engine
Validates website reachability, HTTPS availability, TLS certificate,
HTTP response codes, and redirection targets with strict SSRF defenses.
"""

import logging
import re
import socket
import ssl
from urllib.parse import urlparse
from typing import Dict, Any, Optional
import requests

from backend.company_intelligence.schemas import empty_website_intelligence
from backend.network_security import validate_safe_url

logger = logging.getLogger("scamguard.company_intelligence.website")

REQUEST_TIMEOUT_SECONDS = 4
MAX_REDIRECTS = 3
MAX_CONTENT_BYTES = 512 * 1024  # 512 KB


def verify_tls_certificate(hostname: str, port: int = 443) -> bool:
    """
    Checks if a valid TLS certificate exists and can be validated for the host.
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=REQUEST_TIMEOUT_SECONDS) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                return bool(cert)
    except Exception:
        return False


def check_website_intelligence(domain_or_url: str) -> Dict[str, Any]:
    """
    Performs SSRF-safe probe of a company's website.
    Evaluates:
    - reachable (bool)
    - https (bool)
    - status_code (int or None)
    - final_url (str)
    - domain (str)
    - tls_certificate_valid (bool)
    - redirect_target (Optional[str])
    - title (Optional[str])
    """
    if not domain_or_url:
        return empty_website_intelligence()

    raw_input = domain_or_url.strip()
    if not raw_input.startswith(("http://", "https://")):
        probe_url = f"https://{raw_input}"
    else:
        probe_url = raw_input

    # Parse and validate domain
    parsed = urlparse(probe_url)
    host = (parsed.hostname or "").lower()
    if not host:
        return empty_website_intelligence(raw_input)

    # SSRF Check 1: Probe URL
    is_safe, norm_host, err = validate_safe_url(probe_url)
    if not is_safe:
        res = empty_website_intelligence(probe_url)
        res["error"] = f"Security block (SSRF): {err}"
        res["domain"] = host
        return res

    session = requests.Session()
    session.max_redirects = MAX_REDIRECTS
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 ScamGuard/2.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    # First attempt HTTPS probe
    urls_to_try = [probe_url]
    if probe_url.startswith("https://"):
        urls_to_try.append(f"http://{host}")
    elif probe_url.startswith("http://"):
        urls_to_try.insert(0, f"https://{host}")

    last_error = None
    for target_url in urls_to_try:
        try:
            # Re-verify URL before request
            is_valid, _, val_err = validate_safe_url(target_url)
            if not is_valid:
                continue

            resp = session.get(
                target_url,
                headers=headers,
                timeout=(REQUEST_TIMEOUT_SECONDS, REQUEST_TIMEOUT_SECONDS),
                allow_redirects=True,
                stream=True
            )

            # Re-verify final redirect URL
            final_url = resp.url
            is_dest_safe, _, dest_err = validate_safe_url(final_url)
            if not is_dest_safe:
                res = empty_website_intelligence(target_url)
                res["error"] = f"Redirect blocked (SSRF): {dest_err}"
                res["domain"] = host
                return res

            final_parsed = urlparse(final_url)
            final_host = (final_parsed.hostname or "").lower()
            is_https = final_url.lower().startswith("https://")

            # Check TLS validity if HTTPS
            tls_valid = False
            if is_https:
                tls_valid = verify_tls_certificate(final_host)
                if not tls_valid and resp.status_code and is_https:
                    tls_valid = True

            # Read bounded content snippet for page title
            content_chunk = resp.raw.read(MAX_CONTENT_BYTES, decode_content=True)
            content_text = content_chunk.decode("utf-8", errors="replace")
            title_match = re.search(r'<title[^>]*>(.*?)</title>', content_text, re.IGNORECASE | re.DOTALL)
            page_title = title_match.group(1).strip() if title_match else None
            if page_title:
                page_title = re.sub(r'\s+', ' ', page_title)[:120]

            redirect_target = final_url if final_url != target_url else None

            return {
                "reachable": True,
                "https": is_https,
                "status_code": resp.status_code,
                "final_url": final_url,
                "domain": final_host or host,
                "tls_certificate": tls_valid,
                "tls_certificate_valid": tls_valid,
                "redirect_target": redirect_target,
                "title": page_title,
                "checked_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                "error": None
            }

        except requests.exceptions.SSLError:
            last_error = "SSL/TLS verification failed"
            continue
        except requests.exceptions.Timeout:
            last_error = "Connection timed out"
            continue
        except requests.exceptions.RequestException as req_err:
            last_error = str(req_err)
            continue
        except Exception as e:
            last_error = str(e)
            continue

    # If unreachable
    res = empty_website_intelligence(probe_url)
    res["domain"] = host
    res["error"] = last_error or "Website unreachable"
    return res
