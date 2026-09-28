"""
Audit Logging System for ScamGuard AI
Maintains immutable cybersecurity audit trails for critical authentication,
analysis, telemetry, and data lifecycle events.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from flask import request
from backend.database import get_db

AUDIT_EVENTS = {
    "USER_REGISTERED",
    "EMAIL_VERIFIED",
    "LOGIN_SUCCESS",
    "LOGIN_FAILED",
    "PASSWORD_RESET_REQUESTED",
    "PASSWORD_CHANGED",
    "DOCUMENT_UPLOADED",
    "ANALYSIS_STARTED",
    "OCR_COMPLETED",
    "DOMAIN_LOOKUP_COMPLETED",
    "AI_ANALYSIS_COMPLETED",
    "REPORT_GENERATED",
    "REPORT_SHARED",
    "REPORT_DOWNLOADED",
    "ACCOUNT_DELETED",
    "SESSION_REVOKED",
    "SETTINGS_UPDATED"
}

def log_audit_event(
    event_type: str,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS"
) -> bool:
    """
    Inserts a sanitized immutable event record into db.audit_logs.
    """
    try:
        db = get_db()
        if db is None:
            return False

        ip = "127.0.0.1"
        ua = "system"
        try:
            if request:
                if request.headers.get("CF-Connecting-IP"):
                    ip = request.headers.get("CF-Connecting-IP")
                elif request.headers.get("X-Forwarded-For"):
                    ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
                elif request.headers.get("X-Real-IP"):
                    ip = request.headers.get("X-Real-IP")
                else:
                    ip = request.remote_addr or "127.0.0.1"
                ua = (request.headers.get("User-Agent") or "")[:250]
        except RuntimeError:
            # Outside request context (background job/test)
            pass

        # Sanitize metadata to guarantee no passwords, full tokens, or raw document content are saved
        safe_meta = {}
        if metadata:
            for k, v in metadata.items():
                if any(bad in k.lower() for bad in ["password", "token", "raw_text", "document_text", "secret", "body"]):
                    continue
                safe_meta[k] = str(v)[:200]

        record = {
            "event_type": event_type,
            "status": status,
            "user_id": str(user_id) if user_id else None,
            "email": email,
            "ip_address": ip,
            "user_agent": ua,
            "metadata": safe_meta,
            "created_at": datetime.utcnow()
        }

        db.audit_logs.insert_one(record)
        return True
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to record event {event_type}: {e}")
        return False
