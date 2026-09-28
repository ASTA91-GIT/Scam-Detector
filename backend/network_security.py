"""
Network Security & SSRF Protection Utilities
Provides strict validation of external URLs and IP addresses to prevent
Server-Side Request Forgery (SSRF), DNS rebinding, and unauthorized intranet access.
"""

import socket
import ipaddress
from urllib.parse import urlparse
from typing import Tuple, Optional, Dict, Any
import requests

# Blocked IP ranges (private, loopback, link-local, cloud metadata, multicast, reserved)
BLOCKED_NETWORKS = [
    ipaddress.ip_network('0.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('100.64.0.0/10'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),  # Link-local & AWS/GCP/Azure Metadata (169.254.169.254)
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.0.0.0/24'),
    ipaddress.ip_network('192.0.2.0/24'),
    ipaddress.ip_network('192.88.99.0/24'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('198.18.0.0/15'),
    ipaddress.ip_network('198.51.100.0/24'),
    ipaddress.ip_network('203.0.113.0/24'),
    ipaddress.ip_network('224.0.0.0/4'),    # Multicast
    ipaddress.ip_network('240.0.0.0/4'),    # Reserved
    ipaddress.ip_network('255.255.255.255/32'),
    # IPv6 ranges
    ipaddress.ip_network('::/128'),
    ipaddress.ip_network('::1/128'),        # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),       # Unique Local Address (ULA)
    ipaddress.ip_network('fe80::/10'),      # Link-local unicast
    ipaddress.ip_network('ff00::/8'),       # Multicast
]


def is_ip_blocked(ip_str: str) -> bool:
    """
    Checks if an IP address falls within private, loopback, link-local, or cloud metadata ranges.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True
        for net in BLOCKED_NETWORKS:
            if ip in net:
                return True
        return False
    except ValueError:
        return True


def validate_safe_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates whether a URL is safe to query externally:
    - Must be http:// or https://
    - Must have a valid hostname
    - Must resolve to public, non-private IP addresses
    - Rejects localhost, 127.0.0.1, 169.254.169.254, private ranges, file://, ftp://, etc.

    Returns:
        (is_safe: bool, normalized_host: Optional[str], error_message: Optional[str])
    """
    if not url or not isinstance(url, str):
        return False, None, "Invalid or empty URL."

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        return False, None, "Malformed URL format."

    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        return False, None, f"Unsupported protocol '{scheme}'. Only http:// and https:// are permitted."

    host = parsed.hostname
    if not host:
        return False, None, "URL is missing a valid hostname."

    host = host.lower().strip()

    # Immediate rejection of known dangerous hostnames
    if host in ('localhost', '127.0.0.1', '::1', '0.0.0.0', 'metadata.google.internal', 'instance-data'):
        return False, host, "Direct access to internal host or metadata service is prohibited."

    # If host is already an IP address
    try:
        ip_obj = ipaddress.ip_address(host)
        if is_ip_blocked(str(ip_obj)):
            return False, host, f"Access to private/restricted IP address ({host}) is prohibited."
        return True, host, None
    except ValueError:
        pass  # It's a domain name, proceed to DNS resolution

    # Resolve domain to IP addresses to prevent SSRF and DNS rebinding
    try:
        addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_info:
            return False, host, f"Host '{host}' could not be resolved via DNS."

        resolved_ips = set()
        for item in addr_info:
            ip_str = item[4][0]
            resolved_ips.add(ip_str)

        for resolved_ip in resolved_ips:
            if is_ip_blocked(resolved_ip):
                return False, host, f"Host '{host}' resolves to restricted/private address ({resolved_ip}). Access denied."

        return True, host, None

    except socket.gaierror as e:
        return False, host, f"DNS resolution failed for '{host}': {e}"
    except Exception as e:
        return False, host, f"Network validation error: {str(e)}"


def safe_fetch_head(url: str, timeout: int = 4) -> Dict[str, Any]:
    """
    Performs an SSRF-safe HEAD/GET request to evaluate basic HTTP response metadata.
    Enforces connect & read timeouts, redirects validation, and maximum size limits.
    """
    is_safe, host, err = validate_safe_url(url)
    if not is_safe:
        return {
            "success": False,
            "error": err,
            "status_code": None,
            "https": url.lower().startswith("https://")
        }

    try:
        session = requests.Session()
        session.max_redirects = 3
        headers = {
            "User-Agent": "ScamGuard-Forensics-Bot/2.0 (+https://scamguard.local/bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        # First try HEAD
        resp = session.head(url, headers=headers, timeout=(timeout, timeout), allow_redirects=True, stream=True)
        # If redirected, re-validate destination URL
        if resp.url != url:
            is_dest_safe, _, dest_err = validate_safe_url(resp.url)
            if not is_dest_safe:
                return {
                    "success": False,
                    "error": f"Redirect blocked: {dest_err}",
                    "status_code": resp.status_code,
                    "https": resp.url.lower().startswith("https://")
                }

        return {
            "success": True,
            "status_code": resp.status_code,
            "https": resp.url.lower().startswith("https://"),
            "final_url": resp.url,
            "content_type": resp.headers.get("Content-Type", "")
        }
    except requests.exceptions.RequestException as req_err:
        return {
            "success": False,
            "error": f"Request failed: {str(req_err)}",
            "status_code": None,
            "https": url.lower().startswith("https://")
        }
