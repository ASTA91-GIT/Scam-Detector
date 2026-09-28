"""
Internal Mail Service Client for ScamGuard AI
Dispatches transactional, verification, and security alert emails
via the dedicated Node.js Nodemailer microservice.
"""

import os
import requests
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

MAIL_SERVICE_URL = os.getenv("MAIL_SERVICE_URL", "http://localhost:5001")
MAIL_SERVICE_SECRET = os.getenv("MAIL_SERVICE_SECRET", "dev-internal-mail-secret")


def _dispatch_request(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Internal synchronous POST to the mail microservice."""
    try:
        headers = {
            "Authorization": f"Bearer {MAIL_SERVICE_SECRET}",
            "Content-Type": "application/json"
        }
        url = f"{MAIL_SERVICE_URL.rstrip('/')}/internal/send-email"
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"[MAIL CLIENT] Dispatch returned code {resp.status_code}: {resp.text}")
        return None
    except Exception as e:
        logger.error(f"[MAIL CLIENT] Failed to connect to mail service at {MAIL_SERVICE_URL}: {e}")
        return None


def send_email(
    to: str,
    template: str,
    subject: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    async_dispatch: bool = True
) -> bool:
    """
    Sends an email via the internal Node.js Nodemailer service.
    
    :param to: Recipient email address
    :param template: Template name (e.g. 'welcome', 'verify-email', 'security-alert')
    :param subject: Custom subject line (optional)
    :param data: Variables passed to the template
    :param async_dispatch: If True, fires in a background daemon thread
    """
    payload = {
        "to": to,
        "template": template,
        "subject": subject,
        "data": data or {}
    }

    if async_dispatch:
        thread = threading.Thread(target=_dispatch_request, args=(payload,), daemon=True)
        thread.start()
        return True
    else:
        res = _dispatch_request(payload)
        return res is not None and res.get("success", False)


def check_mail_health() -> Dict[str, Any]:
    """
    Health check probe for the mail microservice.
    """
    try:
        url = f"{MAIL_SERVICE_URL.rstrip('/')}/health"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            info = resp.json()
            return {
                "status": "healthy",
                "simulator": info.get("simulator", False),
                "uptime": info.get("uptime", 0)
            }
        return {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}
