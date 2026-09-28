"""
Session and Client Telemetry Utilities
Parses User-Agent strings, extracts client IP, and manages active session records.
"""

import re
import uuid
from datetime import datetime
from flask import request
from typing import Dict, Any, Optional

def parse_user_agent(ua_string: str) -> Dict[str, str]:
    """Extracts browser and operating system details from User-Agent string."""
    ua = ua_string or ""
    
    # OS Detection
    os_name = "Unknown OS"
    if "Windows NT 10.0" in ua:
        os_name = "Windows 10/11"
    elif "Windows NT" in ua:
        os_name = "Windows"
    elif "Macintosh" in ua or "Mac OS X" in ua:
        os_name = "macOS"
    elif "Android" in ua:
        os_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    elif "Linux" in ua:
        os_name = "Linux"

    # Browser Detection
    browser_name = "Unknown Browser"
    if "Edg/" in ua:
        browser_name = "Microsoft Edge"
    elif "Chrome/" in ua and "Safari/" in ua:
        browser_name = "Google Chrome"
    elif "Firefox/" in ua:
        browser_name = "Mozilla Firefox"
    elif "Safari/" in ua and "Chrome/" not in ua:
        browser_name = "Apple Safari"
    elif "Opera" in ua or "OPR/" in ua:
        browser_name = "Opera"

    return {
        "browser": browser_name,
        "os": os_name,
        "device": f"{browser_name} on {os_name}"
    }


def get_client_ip() -> str:
    """Retrieves real client IP taking into account reverse proxy headers."""
    if request.headers.get("CF-Connecting-IP"):
        return request.headers.get("CF-Connecting-IP")
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    if request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    return request.remote_addr or "127.0.0.1"


def create_session_record(user_id: str) -> Dict[str, Any]:
    """Constructs a new active session metadata dictionary."""
    ua_str = request.headers.get("User-Agent", "")
    client_info = parse_user_agent(ua_str)
    now = datetime.utcnow()
    
    return {
        "session_id": str(uuid.uuid4()),
        "user_id": str(user_id),
        "ip_address": get_client_ip(),
        "user_agent": ua_str[:300],
        "browser": client_info["browser"],
        "os": client_info["os"],
        "device": client_info["device"],
        "created_at": now,
        "last_seen": now,
        "revoked": False
    }
