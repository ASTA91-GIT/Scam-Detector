"""
ScamGuard AI - Webhook Dispatcher
Handles cryptographically signed outbound webhooks for forensic events:
- analysis.completed
- analysis.high_risk
- analysis.failed
- report.created
"""

import hmac
import hashlib
import json
import time
import requests
import threading
from datetime import datetime
from bson import ObjectId
from backend.database import get_webhooks_collection, get_webhook_deliveries_collection

def compute_signature(payload_bytes: bytes, secret: str) -> str:
    """Computes HMAC-SHA256 signature for webhook payload verification."""
    return hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()

def sign_webhook_payload(secret: str, payload) -> str:
    """Signs payload string or bytes and returns header formatted signature sha256=..."""
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    return f"sha256={compute_signature(payload, secret)}"

def dispatch_webhook_event(user_id: str, event_name: str, payload_data: dict):
    """
    Asynchronously finds all active user webhooks subscribed to event_name,
    signs the payload, and sends HTTP POST requests with retry telemetry.
    """
    def _worker():
        try:
            webhooks_col = get_webhooks_collection()
            deliveries_col = get_webhook_deliveries_collection()
            if webhooks_col is None:
                return

            query = {
                'user_id': str(user_id),
                'active': True,
                '$or': [
                    {'events': event_name},
                    {'events': '*'}
                ]
            }

            active_hooks = list(webhooks_col.find(query))
            if not active_hooks:
                return

            timestamp = int(time.time())
            envelope = {
                'event': event_name,
                'timestamp': timestamp,
                'data': payload_data
            }
            payload_str = json.dumps(envelope, default=str)
            payload_bytes = payload_str.encode('utf-8')

            for hook in active_hooks:
                webhook_id = str(hook['_id'])
                url = hook.get('url')
                secret = hook.get('secret', 'scamguard-default-secret')
                signature = compute_signature(payload_bytes, secret)

                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'ScamGuard-AI-Webhook/1.0',
                    'X-ScamGuard-Event': event_name,
                    'X-ScamGuard-Signature': f"sha256={signature}",
                    'X-ScamGuard-Timestamp': str(timestamp)
                }

                status_code = None
                error_msg = None
                success = False

                try:
                    res = requests.post(url, data=payload_bytes, headers=headers, timeout=5)
                    status_code = res.status_code
                    success = 200 <= res.status_code < 300
                except Exception as ex:
                    error_msg = str(ex)

                if deliveries_col is not None:
                    deliveries_col.insert_one({
                        'webhook_id': webhook_id,
                        'user_id': str(user_id),
                        'event': event_name,
                        'url': url,
                        'status_code': status_code,
                        'success': success,
                        'error': error_msg,
                        'created_at': datetime.utcnow()
                    })

        except Exception as e:
            # Silent background log to prevent blocking primary analysis flow
            print(f"[WEBHOOK WORKER ERROR] {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
