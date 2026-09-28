"""
ScamGuard AI - Production Preflight Verification Script
Performs end-to-end infrastructure, service, and security checks before deployment.
"""

import sys
import os
import shutil
from dotenv import load_dotenv

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# Reconfigure stdout for utf-8 if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_preflight():
    print("=" * 65)
    print("  SCAMGUARD AI — PRODUCTION PREFLIGHT CHECK")
    print("=" * 65)

    blockers = []
    checks = []

    # 1. Environment Variables & Security Config
    flask_env = os.getenv("FLASK_ENV", "development")
    secret_key = os.getenv("SECRET_KEY", "")
    jwt_secret = os.getenv("JWT_SECRET", "")
    is_safe_secrets = True

    if not secret_key or secret_key in ("dev-secret-key", "default-insecure-secret"):
        if flask_env == "production":
            blockers.append("SECRET_KEY is using an insecure or default value in production.")
            is_safe_secrets = False

    if not jwt_secret or jwt_secret in ("jwt-secret-key", "dev-jwt-secret"):
        if flask_env == "production":
            blockers.append("JWT_SECRET is using an insecure default value in production.")
            is_safe_secrets = False

    if is_safe_secrets:
        checks.append("[✓] Configuration & Environment Variables")
    else:
        checks.append("[✗] Configuration (Insecure secrets detected)")

    # 2. MongoDB Connectivity & Indexes
    mongo_ok = False
    try:
        from backend.database import get_database, init_db
        init_db()
        db = get_database()
        db.command("ping")
        indexes = db.users.index_information()
        if "email_1" in indexes:
            mongo_ok = True
            checks.append("[✓] MongoDB Connection & Required Indexes")
        else:
            blockers.append("MongoDB is connected but required unique indexes are missing.")
            checks.append("[✗] MongoDB (Missing indexes)")
    except Exception as me:
        blockers.append(f"MongoDB connection failed: {me}")
        checks.append(f"[✗] MongoDB ({me})")

    # 3. Ollama Connectivity & Authoritative Model Availability
    ollama_ok = False
    try:
        from backend.ai.provider_factory import get_ai_status
        ai_stat = get_ai_status()
        if ai_stat.get("available"):
            ollama_ok = True
            checks.append(f"[✓] Ollama Engine & Model ({ai_stat.get('model')})")
        else:
            blockers.append(f"Ollama is unreachable or model is not loaded: {ai_stat.get('error', 'Unknown error')}")
            checks.append("[✗] Ollama Engine & Model Availability")
    except Exception as oe:
        blockers.append(f"Ollama health check error: {oe}")
        checks.append(f"[✗] Ollama ({oe})")

    # 4. OCR & PDF Processing Dependencies
    ocr_ok = True
    ocr_details = []
    try:
        import pypdfium2
        ocr_details.append("pypdfium2: OK")
    except ImportError:
        ocr_ok = False
        blockers.append("pypdfium2 is not installed.")

    try:
        import PyPDF2
        ocr_details.append("PyPDF2: OK")
    except ImportError:
        ocr_ok = False
        blockers.append("PyPDF2 is not installed.")

    try:
        from PIL import Image
        ocr_details.append("Pillow: OK")
    except ImportError:
        ocr_ok = False
        blockers.append("Pillow is not installed.")

    tesseract_found = shutil.which("tesseract") is not None
    if not tesseract_found:
        # Check standard Windows paths
        win_tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(win_tess):
            tesseract_found = True

    if tesseract_found:
        ocr_details.append("Tesseract OCR: OK")
    else:
        ocr_details.append("Tesseract OCR: Scanned PDF fallback degraded (native PDF & vision active)")

    if ocr_ok:
        checks.append(f"[✓] OCR & Document Pipeline ({', '.join(ocr_details[:3])})")
    else:
        checks.append("[✗] OCR & Document Pipeline")

    # 5. Node.js Mail Service Connectivity
    mail_ok = False
    try:
        from backend.mail_client import check_mail_health
        m_stat = check_mail_health()
        if m_stat.get("status") == "healthy":
            mail_ok = True
            mode = "Simulator" if m_stat.get("simulator") else "SMTP Live"
            checks.append(f"[✓] Node.js Mail Service ({mode})")
        else:
            blockers.append(f"Mail service health degraded: {m_stat.get('error', 'Unreachable')}")
            checks.append("[✗] Mail Service")
    except Exception as mle:
        blockers.append(f"Mail service probe error: {mle}")
        checks.append(f"[✗] Mail Service ({mle})")

    # 6. Domain Intelligence & SSRF Protection
    domain_ok = False
    try:
        from backend.network_security import validate_safe_url, is_ip_blocked
        from backend.forensic_utils import detect_lookalike_domain

        # Verify loopback is blocked
        is_safe, _, _ = validate_safe_url("http://127.0.0.1:5000/internal")
        lookalike = detect_lookalike_domain("paypa1.com")

        if not is_safe and lookalike.get("possible_lookalike"):
            domain_ok = True
            checks.append("[✓] Domain Intelligence & SSRF Protection Filters")
        else:
            blockers.append("SSRF filter failed to block loopback request or lookalike detection failed.")
            checks.append("[✗] Domain Intelligence & SSRF Protection")
    except Exception as de:
        blockers.append(f"Domain intelligence test failed: {de}")
        checks.append(f"[✗] Domain Intelligence ({de})")

    # 7. Upload Directory & Storage Permissions
    storage_ok = False
    try:
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        test_file = os.path.join(upload_dir, ".test_write")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        storage_ok = True
        checks.append("[✓] Upload Directory Storage Permissions")
    except Exception as se:
        blockers.append(f"Upload directory write test failed: {se}")
        checks.append(f"[✗] Upload Directory Storage Permissions ({se})")

    # 8. Security Configuration & Production Debug Mode
    debug_ok = True
    if flask_env == "production" and os.getenv("DEBUG", "false").lower() in ("true", "1"):
        blockers.append("Debug mode is enabled while FLASK_ENV=production.")
        debug_ok = False
        checks.append("[✗] Security Configuration (Debug enabled in production)")
    else:
        checks.append("[✓] Security Configuration (Debug disabled)")

    print()
    for c in checks:
        print(f"  {c}")
    print()

    if not blockers:
        print("=" * 65)
        print("  RESULT: READY FOR DEPLOYMENT")
        print("=" * 65)
        return True
    else:
        print("=" * 65)
        print("  RESULT: DEPLOYMENT BLOCKED")
        print("=" * 65)
        print("\nBlockers:")
        for idx, b in enumerate(blockers, 1):
            print(f"  {idx}. {b}")
        print()
        return False


if __name__ == "__main__":
    success = run_preflight()
    sys.exit(0 if success else 1)
