"""
Comprehensive Production Readiness Test Suite for ScamGuard AI
Tests all major security, upload, authentication, domain intelligence,
report sharing, and error handling capabilities.
"""

import pytest
import os
import sys
import io
import json
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from backend.database import get_database, get_users_collection, get_analyses_collection
from backend.network_security import validate_safe_url, is_ip_blocked
from backend.forensic_utils import detect_lookalike_domain, extract_url_intelligence
from backend.file_utils import validate_file_security, allowed_file
from backend.rate_limiter import apply_rate_limit
from backend.mail_client import check_mail_health


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# ============================================================
# 1. NETWORK SECURITY & SSRF PROTECTION TESTS
# ============================================================

def test_ssrf_blocks_localhost():
    is_safe, _, msg = validate_safe_url("http://localhost:5000/internal")
    assert is_safe is False

def test_ssrf_blocks_loopback_ip():
    is_safe, _, msg = validate_safe_url("http://127.0.0.1:8080")
    assert is_safe is False

def test_ssrf_blocks_cloud_metadata():
    is_safe, _, msg = validate_safe_url("http://169.254.169.254/latest/meta-data/")
    assert is_safe is False

def test_ssrf_blocks_private_ranges():
    assert validate_safe_url("http://10.0.0.1/admin")[0] is False
    assert validate_safe_url("http://192.168.1.100/router")[0] is False
    assert validate_safe_url("http://172.16.0.5/api")[0] is False

def test_ssrf_blocks_arbitrary_schemes():
    assert validate_safe_url("file:///etc/passwd")[0] is False
    assert validate_safe_url("ftp://ftp.example.com")[0] is False
    assert validate_safe_url("gopher://example.com")[0] is False

def test_ssrf_allows_legitimate_public_url():
    is_safe, host, _ = validate_safe_url("https://google.com")
    assert is_safe is True
    assert host == "google.com"


# ============================================================
# 2. DOMAIN & LOOKALIKE DETECTION TESTS
# ============================================================

def test_lookalike_detects_micros0ft():
    res = detect_lookalike_domain("micros0ft.com")
    assert res["possible_lookalike"] is True
    assert res["matched_brand"] == "Microsoft"

def test_lookalike_detects_paypa1():
    res = detect_lookalike_domain("paypa1.com")
    assert res["possible_lookalike"] is True
    assert res["matched_brand"] == "PayPal"

def test_lookalike_identifies_legitimate_brand():
    res = detect_lookalike_domain("google.com")
    assert res["possible_lookalike"] is False
    assert res["matched_brand"] == "Google"

def test_url_intelligence_extraction():
    sample_text = "Please submit your documents to https://paypa1.com/verify or visit https://microsoft.com for details."
    urls = extract_url_intelligence(sample_text)
    assert len(urls) >= 2
    domains = [u["domain"] for u in urls]
    assert "paypa1.com" in domains
    assert "microsoft.com" in domains


# ============================================================
# 3. UPLOAD SECURITY & MAGIC BYTES TESTS
# ============================================================

class DummyFile:
    def __init__(self, filename, content):
        self.filename = filename
        self.stream = io.BytesIO(content)


def test_upload_rejects_executables():
    # MZ header (Windows PE executable)
    fake_exe = DummyFile("resume.pdf", b"MZ\x90\x00\x03\x00\x00\x00")
    is_valid, ext, err = validate_file_security(fake_exe)
    assert is_valid is False
    assert "Executable" in err or "Malicious" in err

def test_upload_rejects_fake_extension():
    # PNG extension with arbitrary text content
    fake_png = DummyFile("test.png", b"Hello this is just text not a PNG")
    is_valid, ext, err = validate_file_security(fake_png)
    assert is_valid is False
    assert "Magic byte mismatch" in err

def test_upload_allows_valid_magic_bytes():
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new('RGB', (100, 100), color=(255, 255, 255))
    img.save(buf, format='PNG')
    buf.seek(0)

    dummy_png = DummyFile("test_sample.png", buf.getvalue())
    is_valid, ext, err = validate_file_security(dummy_png)
    assert is_valid is True
    assert ext == "png"


# ============================================================
# 4. SYSTEM HEALTH & ERROR HANDLING TESTS
# ============================================================

def test_health_endpoint(client):
    res = client.get('/api/health')
    assert res.status_code == 200
    data = res.get_json()
    assert "services" in data
    assert data["services"]["api"] == "healthy"
    assert data["services"]["database"] == "healthy"

def test_ready_endpoint(client):
    res = client.get('/api/ready')
    assert res.status_code == 200
    assert res.get_json()["status"] == "ready"

def test_security_headers_present(client):
    res = client.get('/api/health')
    assert 'X-Request-ID' in res.headers
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'
    assert res.headers.get('X-Frame-Options') == 'DENY'
    assert 'Content-Security-Policy' in res.headers

def test_standardized_error_format(client):
    res = client.get('/api/non-existent-endpoint')
    assert res.status_code == 404
    data = res.get_json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "request_id" in data["error"]


# ============================================================
# 5. RATE LIMITING TESTS
# ============================================================

def test_rate_limiter_throttles():
    key = f"test-bucket:{uuid.uuid4().hex}"
    # 3 calls allowed in 5 seconds
    assert apply_rate_limit(key, limit=3, window_seconds=5)[0] is True
    assert apply_rate_limit(key, limit=3, window_seconds=5)[0] is True
    assert apply_rate_limit(key, limit=3, window_seconds=5)[0] is True
    # 4th call should be rejected
    is_allowed, msg = apply_rate_limit(key, limit=3, window_seconds=5)
    assert is_allowed is False
    assert "Rate limit exceeded" in msg


# ============================================================
# 6. REPORT SHARING & PUBLIC VERIFICATION TESTS
# ============================================================

def test_public_report_verification_endpoint(client):
    # Query an invalid public ID
    res = client.get('/api/saved-reports/verify/SG-NONEXIST')
    assert res.status_code == 404
    assert res.get_json()["valid"] is False


# ============================================================
# 7. AUTH & TOKEN VERSION TESTS
# ============================================================

def test_unauthorized_access_rejected(client):
    res = client.get('/api/admin/metrics')
    # Should be 401 Unauthorized without token
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "UNAUTHORIZED"
