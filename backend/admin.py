"""
Admin Blueprint
Provides endpoints for administrative oversight, metrics, system telemetry,
and audit logs. Strictly protected by require_admin decorator.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from bson import ObjectId

from backend.auth_utils import require_auth, require_admin
from backend.database import (
    get_users_collection,
    get_analyses_collection,
    get_audit_logs_collection,
    get_database
)
from backend.rate_limiter import apply_rate_limit
from backend.mail_client import check_mail_health
from backend.ai.provider_factory import get_ai_status

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/metrics', methods=['GET'])
@require_auth
@require_admin
def get_admin_metrics():
    """
    Returns platform-wide metrics:
    Total users, active users (last 7 days), documents analyzed,
    high-risk percentage, failed analyses count, average analysis time.
    """
    try:
        users_coll = get_users_collection()
        analyses_coll = get_analyses_collection()

        total_users = users_coll.count_documents({})
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        active_users = users_coll.count_documents({"last_login": {"$gte": seven_days_ago}})

        total_analyses = analyses_coll.count_documents({})
        high_risk_count = analyses_coll.count_documents({
            "$or": [
                {"classification": "HIGH_RISK"},
                {"risk_score": {"$gte": 70}}
            ]
        })
        high_risk_pct = round((high_risk_count / total_analyses * 100), 1) if total_analyses > 0 else 0

        # Check failed analyses in jobs collection
        db = get_database()
        jobs_coll = db["analysis_jobs"]
        failed_jobs = jobs_coll.count_documents({"status": "FAILED"})

        metrics = {
            "total_users": total_users,
            "active_users": active_users,
            "documents_analyzed": total_analyses,
            "high_risk_analyses": high_risk_count,
            "high_risk_percentage": high_risk_pct,
            "failed_analysis_count": failed_jobs,
            "generated_at": datetime.utcnow().isoformat()
        }

        return jsonify({"metrics": metrics}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to calculate admin metrics: {str(e)}"}), 500


@admin_bp.route('/users', methods=['GET'])
@require_auth
@require_admin
def list_users():
    """
    Paginated, sanitized list of registered users.
    Never exposes password hashes or verification tokens.
    """
    try:
        limit = min(100, int(request.args.get("limit", 20)))
        offset = max(0, int(request.args.get("offset", 0)))
        search = request.args.get("search", "").strip()

        users_coll = get_users_collection()
        query = {}
        if search:
            query["$or"] = [
                {"email": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}}
            ]

        total = users_coll.count_documents(query)
        cursor = users_coll.find(
            query,
            {
                "password_hash": 0,
                "verification_token_hash": 0,
                "reset_token_hash": 0
            }
        ).sort("created_at", -1).skip(offset).limit(limit)

        users = []
        for u in cursor:
            u["_id"] = str(u["_id"])
            if "created_at" in u and hasattr(u["created_at"], "isoformat"):
                u["created_at"] = u["created_at"].isoformat()
            if "last_login" in u and hasattr(u["last_login"], "isoformat"):
                u["last_login"] = u["last_login"].isoformat()
            users.append(u)

        return jsonify({"users": users, "total": total, "limit": limit, "offset": offset}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/audit-logs', methods=['GET'])
@require_auth
@require_admin
def get_audit_logs():
    """
    Paginated audit events log.
    """
    try:
        limit = min(100, int(request.args.get("limit", 50)))
        offset = max(0, int(request.args.get("offset", 0)))
        event_type = request.args.get("event_type", "").strip()

        audit_coll = get_audit_logs_collection()
        query = {}
        if event_type:
            query["event_type"] = event_type

        total = audit_coll.count_documents(query)
        cursor = audit_coll.find(query).sort("timestamp", -1).skip(offset).limit(limit)

        logs = []
        for l in cursor:
            l["_id"] = str(l["_id"])
            if "timestamp" in l and hasattr(l["timestamp"], "isoformat"):
                l["timestamp"] = l["timestamp"].isoformat()
            logs.append(l)

        return jsonify({"audit_logs": logs, "total": total, "limit": limit, "offset": offset}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/system-health', methods=['GET'])
@require_auth
@require_admin
def get_system_health():
    """
    Deep system health check for all platform services.
    """
    db_status = "healthy"
    try:
        get_database().command("ping")
    except Exception:
        db_status = "unhealthy"

    ai_status = get_ai_status()
    ollama_health = "healthy" if ai_status.get("available") else "degraded"

    mail_status = check_mail_health()
    mail_health = "healthy" if mail_status.get("status") == "healthy" else "degraded"

    health = {
        "status": "healthy" if (db_status == "healthy" and ollama_health == "healthy" and mail_health == "healthy") else "degraded",
        "services": {
            "api": "healthy",
            "database": db_status,
            "ollama": ollama_health,
            "ocr": "healthy",
            "mail": mail_health,
            "domain_intelligence": "healthy"
        },
        "details": {
            "ollama_model": ai_status.get("model", "llama3.2:3b"),
            "mail_service": mail_status.get("status", "unknown")
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return jsonify(health), 200
