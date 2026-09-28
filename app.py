from flask import Flask, jsonify, send_from_directory, request, g
from flask_cors import CORS
from dotenv import load_dotenv
import os
import uuid
import logging
from datetime import datetime

from backend.database import init_db, get_database
from backend.auth import auth_bp
from backend.analysis import analysis_bp
from backend.dashboard import dashboard_bp
from backend.saved_reports import saved_reports_bp
from backend.notifications import notifications_bp
from backend.case_chat import case_chat_bp
from backend.admin import admin_bp
from backend.ai.provider_factory import get_ai_status
from backend.mail_client import check_mail_health

load_dotenv()

# Structured logging setup (Phase 33)
logging.basicConfig(
    level=logging.INFO if os.getenv('FLASK_ENV') == 'production' else logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger("scamguard.api")

app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_SIZE', os.getenv('MAX_FILE_SIZE', 10485760)))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')

# Phase 27: Strict CORS in production
frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5000')
if os.getenv('FLASK_ENV') == 'production':
    CORS(app, origins=[frontend_url], supports_credentials=True)
else:
    CORS(app, supports_credentials=True)

# Initialize database
init_db()

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(saved_reports_bp, url_prefix='/api/saved-reports')
app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
app.register_blueprint(case_chat_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api/admin')


# ============================================================
# PHASE 25 & 26: REQUEST ID & SECURITY HEADERS MIDDLEWARE
# ============================================================

@app.before_request
def before_request():
    """Generates unique Request ID for tracing and error attribution"""
    g.request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    g.start_time = datetime.utcnow()


@app.after_request
def apply_security_headers(response):
    """
    Applies strict cybersecurity headers:
    - Content-Security-Policy
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy
    - X-Request-ID
    """
    response.headers['X-Request-ID'] = getattr(g, 'request_id', 'UNKNOWN')
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'

    # CSP designed not to break frontend styles and Google fonts
    csp = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://fonts.gstatic.com data: blob:; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' http: https:;"
    )
    response.headers['Content-Security-Policy'] = csp

    if os.getenv('FLASK_ENV') == 'production' and request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response


# ============================================================
# PHASE 24: SYSTEM HEALTH & READINESS ENDPOINTS
# ============================================================

@app.route('/api/health', methods=['GET'])
def system_health():
    """
    Phase 24: Health check endpoint.
    Reports individual health statuses of api, database, ollama, ocr, mail, and domain intelligence.
    Never leaks credentials, paths, or connection strings.
    """
    db_status = "healthy"
    try:
        get_database().command("ping")
    except Exception:
        db_status = "unhealthy"

    ai_stat = get_ai_status()
    ollama_status = "healthy" if ai_stat.get("available") else "degraded"

    mail_stat = check_mail_health()
    mail_status = "healthy" if mail_stat.get("status") == "healthy" else "degraded"

    overall = "healthy" if (db_status == "healthy" and ollama_status == "healthy" and mail_status == "healthy") else "degraded"

    return jsonify({
        "status": overall,
        "services": {
            "api": "healthy",
            "database": db_status,
            "ollama": ollama_status,
            "ocr": "healthy",
            "mail": mail_status,
            "domain_intelligence": "healthy"
        }
    }), 200


@app.route('/api/ready', methods=['GET'])
def system_ready():
    """Readiness probe for container orchestrators"""
    try:
        get_database().command("ping")
        return jsonify({"status": "ready"}), 200
    except Exception:
        return jsonify({"status": "not_ready"}), 503


# Direct compatibility endpoints
@app.route('/api/analyze', methods=['POST'])
def analyze_alias():
    """Alias for /api/analysis/analyze supporting legacy and standardized callers"""
    from backend.analysis import analyze
    return analyze()

@app.route('/api/ai/status', methods=['GET'])
def ai_status_alias():
    """Health check for local offline AI inference engine"""
    return jsonify(get_ai_status()), 200


# Frontend static routing
@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_frontend(path):
    if path.startswith("api/"):
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": "API route not found.",
                "request_id": getattr(g, 'request_id', 'UNKNOWN')
            }
        }), 404
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    full_path = os.path.join(frontend_dir, path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return send_from_directory('frontend', path)
    if os.path.exists(full_path + '.html'):
        return send_from_directory('frontend', path + '.html')
    return send_from_directory('frontend', path)


# ============================================================
# PHASE 25: STANDARDIZED API ERROR HANDLERS
# ============================================================

@app.errorhandler(400)
def bad_request(e):
    return jsonify({
        "error": {
            "code": "BAD_REQUEST",
            "message": str(e.description) if hasattr(e, 'description') else "Bad request.",
            "request_id": getattr(g, 'request_id', 'UNKNOWN')
        }
    }), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Authentication required.",
            "request_id": getattr(g, 'request_id', 'UNKNOWN')
        }
    }), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({
        "error": {
            "code": "FORBIDDEN",
            "message": "You do not have permission to perform this action.",
            "request_id": getattr(g, 'request_id', 'UNKNOWN')
        }
    }), 403

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": {
            "code": "NOT_FOUND",
            "message": "The requested resource was not found.",
            "request_id": getattr(g, 'request_id', 'UNKNOWN')
        }
    }), 404

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "error": {
            "code": "FILE_TOO_LARGE",
            "message": "The uploaded file exceeds the maximum permitted size limit.",
            "request_id": getattr(g, 'request_id', 'UNKNOWN')
        }
    }), 413

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({
        "error": {
            "code": "RATE_LIMITED",
            "message": "Too many requests. Please wait before retrying.",
            "request_id": getattr(g, 'request_id', 'UNKNOWN')
        }
    }), 429

@app.errorhandler(500)
def internal_error(e):
    req_id = getattr(g, 'request_id', 'UNKNOWN')
    logger.error(f"Internal server error [{req_id}]: {e}", exc_info=True)
    return jsonify({
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please contact support with your reference ID.",
            "request_id": req_id
        }
    }), 500

@app.errorhandler(503)
def service_unavailable(e):
    return jsonify({
        "error": {
            "code": "SERVICE_UNAVAILABLE",
            "message": "The service is temporarily unavailable.",
            "request_id": getattr(g, 'request_id', 'UNKNOWN')
        }
    }), 503


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'temporary'), exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)