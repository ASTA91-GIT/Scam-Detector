"""
Sliding-Window In-Memory Rate Limiter for ScamGuard AI
Enforces configurable request limits on sensitive authentication and heavy AI endpoints.
"""

import time
import os
import threading
import uuid
from functools import wraps
from flask import request, jsonify

# Key format: (bucket_name, identifier) -> list of timestamps
_RATE_LIMIT_STORE = {}
_STORE_LOCK = threading.Lock()

def is_rate_limiting_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")


def clean_expired_entries():
    """Periodically cleans timestamps older than 1 hour."""
    now = time.time()
    with _STORE_LOCK:
        keys_to_delete = []
        for key, timestamps in _RATE_LIMIT_STORE.items():
            valid_ts = [t for t in timestamps if now - t < 3600]
            if not valid_ts:
                keys_to_delete.append(key)
            else:
                _RATE_LIMIT_STORE[key] = valid_ts
        for k in keys_to_delete:
            del _RATE_LIMIT_STORE[k]


def get_limiter_key(bucket: str, key_type: str = "ip") -> str:
    if key_type == "user" and hasattr(request, "user_id") and request.user_id:
        return f"{bucket}:user:{request.user_id}"
    
    # Fallback to IP address
    ip = "127.0.0.1"
    if request.headers.get("CF-Connecting-IP"):
        ip = request.headers.get("CF-Connecting-IP")
    elif request.headers.get("X-Forwarded-For"):
        ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
    elif request.headers.get("X-Real-IP"):
        ip = request.headers.get("X-Real-IP")
    elif request.remote_addr:
        ip = request.remote_addr

    return f"{bucket}:ip:{ip}"


def rate_limit(limit: int, window_seconds: int, bucket: str = "default", key_type: str = "ip"):
    """
    Decorator that enforces a sliding window rate limit.
    
    :param limit: Maximum allowed calls in window
    :param window_seconds: Window length in seconds
    :param bucket: Unique bucket name (e.g. 'login', 'register', 'analyze')
    :param key_type: 'ip' or 'user'
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not is_rate_limiting_enabled():
                return f(*args, **kwargs)

            key = get_limiter_key(bucket, key_type)
            now = time.time()
            cutoff = now - window_seconds

            with _STORE_LOCK:
                history = _RATE_LIMIT_STORE.get(key, [])
                history = [t for t in history if t > cutoff]

                if len(history) >= limit:
                    oldest = history[0]
                    retry_after = max(1, int(window_seconds - (now - oldest)))
                    req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
                    
                    return jsonify({
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded. Too many requests for {bucket}. Please retry in {retry_after} seconds.",
                            "retry_after": retry_after,
                            "request_id": req_id
                        }
                    }), 429

                history.append(now)
                _RATE_LIMIT_STORE[key] = history

            return f(*args, **kwargs)
        return wrapper
    return decorator


def apply_rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, str]:
    """
    Direct function to check and apply rate limits.
    Returns (is_allowed: bool, message: str)
    """
    if not is_rate_limiting_enabled():
        return True, ""

    now = time.time()
    cutoff = now - window_seconds

    with _STORE_LOCK:
        history = _RATE_LIMIT_STORE.get(key, [])
        history = [t for t in history if t > cutoff]

        if len(history) >= limit:
            oldest = history[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return False, f"Rate limit exceeded. Please retry in {retry_after} seconds."

        history.append(now)
        _RATE_LIMIT_STORE[key] = history

    return True, ""
