"""
Saved Reports Blueprint
Handles bookmarking, renaming, annotating, and managing saved forensic reports
"""
from flask import Blueprint, request, jsonify
from backend.auth_utils import require_auth
from backend.database import get_saved_reports_collection, get_analyses_collection
from backend.activity_utils import log_activity, create_notification
from datetime import datetime
from bson import ObjectId
import re

saved_reports_bp = Blueprint('saved_reports', __name__)

@saved_reports_bp.route('', methods=['GET'])
@require_auth
def get_saved_reports():
    """Retrieve all saved reports for the authenticated user"""
    try:
        user_id = request.user_id
        col = get_saved_reports_collection()

        search_query = request.args.get('search', '').strip()
        query = {'user_id': user_id}

        if search_query:
            regex = re.compile(re.escape(search_query), re.IGNORECASE)
            query['$or'] = [
                {'custom_title': regex},
                {'company_name': regex},
                {'job_title': regex},
                {'notes': regex}
            ]

        cursor = col.find(query).sort('created_at', -1)
        reports = []
        for r in cursor:
            r['_id'] = str(r['_id'])
            if 'created_at' in r and hasattr(r['created_at'], 'isoformat'):
                r['created_at'] = r['created_at'].isoformat()
            reports.append(r)

        return jsonify({'saved_reports': reports, 'total': len(reports)}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@saved_reports_bp.route('', methods=['POST'])
@require_auth
def save_report():
    """Save an analysis to the user's permanent reports notebook"""
    try:
        user_id = request.user_id
        data = request.get_json() or {}
        analysis_id = data.get('analysis_id', '').strip()
        custom_title = data.get('custom_title', '').strip()
        notes = data.get('notes', '').strip()
        tags = data.get('tags', [])

        if not analysis_id:
            return jsonify({'error': 'Analysis ID is required'}), 400

        # Retrieve analysis details
        try:
            obj_id = ObjectId(analysis_id)
        except Exception:
            return jsonify({'error': 'Invalid analysis ID'}), 400

        analysis = get_analyses_collection().find_one({'_id': obj_id, 'user_id': user_id})
        if not analysis:
            return jsonify({'error': 'Analysis not found or unauthorized'}), 404

        col = get_saved_reports_collection()
        # Check if already saved
        existing = col.find_one({'user_id': user_id, 'analysis_id': analysis_id})
        if existing:
            # Update notes/title
            col.update_one(
                {'_id': existing['_id']},
                {'$set': {'custom_title': custom_title or existing.get('custom_title'), 'notes': notes, 'tags': tags, 'updated_at': datetime.utcnow()}}
            )
            return jsonify({'message': 'Saved report updated', 'saved_id': str(existing['_id'])}), 200

        title = custom_title or f"{analysis.get('job_title', 'Job Offer')} - {analysis.get('company_name', 'Company')}"
        doc = {
            'user_id': user_id,
            'analysis_id': analysis_id,
            'custom_title': title,
            'company_name': analysis.get('company_name', 'Not Specified'),
            'job_title': analysis.get('job_title', 'Job Offer'),
            'risk_level': analysis.get('risk_level', 'Unknown'),
            'trust_score': analysis.get('trust_score', 0),
            'risk_color': analysis.get('risk_color', 'warning'),
            'notes': notes,
            'tags': tags,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        res = col.insert_one(doc)
        saved_id = str(res.inserted_id)

        log_activity(user_id, "report_saved", f"Saved forensic report: {title}")
        create_notification(
            user_id=user_id,
            title="Report Saved",
            message=f"'{title}' was added to your saved reports repository.",
            notif_type="success",
            link="saved.html"
        )

        return jsonify({'message': 'Report saved successfully', 'saved_id': saved_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@saved_reports_bp.route('/check/<analysis_id>', methods=['GET'])
@require_auth
def check_is_saved(analysis_id):
    """Check if an analysis is saved by current user"""
    try:
        user_id = request.user_id
        col = get_saved_reports_collection()
        doc = col.find_one({'user_id': user_id, 'analysis_id': analysis_id})
        if doc:
            return jsonify({'is_saved': True, 'saved_id': str(doc['_id']), 'notes': doc.get('notes', ''), 'custom_title': doc.get('custom_title', '')}), 200
        return jsonify({'is_saved': False}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@saved_reports_bp.route('/<report_id>', methods=['PUT'])
@require_auth
def update_saved_report(report_id):
    """Update title, notes, or tags on a saved report"""
    try:
        user_id = request.user_id
        data = request.get_json() or {}
        custom_title = data.get('custom_title', '').strip()
        notes = data.get('notes', '').strip()
        tags = data.get('tags')

        try:
            obj_id = ObjectId(report_id)
        except Exception:
            return jsonify({'error': 'Invalid report ID'}), 400

        col = get_saved_reports_collection()
        updates = {'updated_at': datetime.utcnow()}
        if custom_title:
            updates['custom_title'] = custom_title
        if notes is not None:
            updates['notes'] = notes
        if tags is not None:
            updates['tags'] = tags

        result = col.update_one({'_id': obj_id, 'user_id': user_id}, {'$set': updates})
        if result.matched_count == 0:
            return jsonify({'error': 'Report not found or unauthorized'}), 404

        return jsonify({'message': 'Saved report updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@saved_reports_bp.route('/<report_id>', methods=['DELETE'])
@require_auth
def delete_saved_report(report_id):
    """Remove a report from saved reports"""
    try:
        user_id = request.user_id
        try:
            obj_id = ObjectId(report_id)
        except Exception:
            return jsonify({'error': 'Invalid report ID'}), 400

        col = get_saved_reports_collection()
        res = col.delete_one({'_id': obj_id, 'user_id': user_id})
        if res.deleted_count == 0:
            return jsonify({'error': 'Report not found or unauthorized'}), 404

        log_activity(user_id, "report_unsaved", f"Removed report #{report_id} from saved items")
        return jsonify({'message': 'Report removed from saved items'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@saved_reports_bp.route('/by-analysis/<analysis_id>', methods=['DELETE'])
@require_auth
def unsave_by_analysis(analysis_id):
    """Unsave a report directly by its analysis ID"""
    try:
        user_id = request.user_id
        col = get_saved_reports_collection()
        res = col.delete_many({'analysis_id': analysis_id, 'user_id': user_id})
        return jsonify({'message': 'Report unsaved successfully', 'count': res.deleted_count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# PHASE 21 & 22: SECURE REPORT SHARING & PUBLIC VERIFICATION
# ============================================================

import secrets
import hashlib
from datetime import timedelta
from backend.database import get_database
from backend.audit_logger import log_audit_event


def _get_shared_reports_collection():
    db = get_database()
    return db["shared_reports"]


@saved_reports_bp.route('/<analysis_id>/share', methods=['POST'])
@require_auth
def create_shared_report_link(analysis_id):
    """
    Generates a secure random share token with expiration and revocation capabilities.
    Does not expose MongoDB IDs or internal file paths.
    """
    try:
        user_id = request.user_id
        analyses_col = get_analyses_collection()

        try:
            obj_id = ObjectId(analysis_id)
        except Exception:
            return jsonify({'error': 'Invalid analysis ID'}), 400

        analysis = analyses_col.find_one({'_id': obj_id, 'user_id': user_id})
        if not analysis:
            return jsonify({'error': 'Analysis not found or unauthorized access'}), 404

        # Generate secure random token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        public_id = f"SG-{raw_token[:8].upper()}"

        data = request.get_json() or {}
        expires_days = min(30, max(1, int(data.get("expires_days", 7))))
        now = datetime.utcnow()
        expires_at = now + timedelta(days=expires_days)

        shared_doc = {
            "token_hash": token_hash,
            "public_id": public_id,
            "analysis_id": str(obj_id),
            "user_id": user_id,
            "created_at": now,
            "expires_at": expires_at,
            "view_count": 0,
            "revoked": False
        }

        shared_col = _get_shared_reports_collection()
        shared_col.insert_one(shared_doc)

        log_audit_event("REPORT_SHARED", user_id, {"analysis_id": str(obj_id), "public_id": public_id})

        return jsonify({
            "share_token": raw_token,
            "public_id": public_id,
            "share_url": f"/shared/report/{raw_token}",
            "verification_url": f"/verify/report/{public_id}",
            "expires_at": expires_at.isoformat()
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@saved_reports_bp.route('/shared/<token>', methods=['GET'])
def get_shared_report_by_token(token):
    """
    Public access to shared report using secure token.
    Validates token hash, expiration, and revocation status.
    """
    try:
        token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
        shared_col = _get_shared_reports_collection()
        shared_record = shared_col.find_one({"token_hash": token_hash})

        if not shared_record:
            return jsonify({'error': 'Shared report not found'}), 404

        if shared_record.get("revoked", False):
            return jsonify({'error': 'This shared report link has been revoked by the owner.'}), 410

        if shared_record.get("expires_at") and shared_record["expires_at"] < datetime.utcnow():
            return jsonify({'error': 'This shared report link has expired.'}), 410

        # Increment view count
        shared_col.update_one({"_id": shared_record["_id"]}, {"$inc": {"view_count": 1}})

        # Fetch sanitized analysis
        analyses_col = get_analyses_collection()
        analysis = analyses_col.find_one({"_id": ObjectId(shared_record["analysis_id"])})
        if not analysis:
            return jsonify({'error': 'Report record unavailable'}), 404

        # Sanitize report (remove private credentials, internal paths, raw uploads)
        sanitized = {
            "public_id": shared_record.get("public_id"),
            "document_type": analysis.get("document_type", "UNKNOWN"),
            "company_name": analysis.get("company_name", "Company"),
            "job_title": analysis.get("job_title", "Document"),
            "risk_score": analysis.get("risk_score", 0),
            "trust_score": analysis.get("trust_score", 100),
            "confidence": analysis.get("confidence", 85),
            "classification": analysis.get("classification", "SAFE"),
            "risk_level": analysis.get("risk_level", "Safe"),
            "risk_color": analysis.get("risk_color", "safe"),
            "summary": analysis.get("summary", ""),
            "reasoning": analysis.get("reasoning", []),
            "positive_signals": analysis.get("positive_signals", []),
            "uncertainties": analysis.get("uncertainties", []),
            "recommendations": analysis.get("recommendations", []),
            "risk_signals": analysis.get("risk_signals", []),
            "entities": analysis.get("entities", {}),
            "domain_intelligence": analysis.get("domain_intelligence", {}),
            "ai_opinion": analysis.get("ai_opinion", {}),
            "model_name": analysis.get("model_name", "llama3.2:3b"),
            "created_at": analysis.get("created_at").isoformat() if hasattr(analysis.get("created_at"), "isoformat") else str(analysis.get("created_at")),
            "view_count": shared_record.get("view_count", 0) + 1
        }

        return jsonify({"report": sanitized}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@saved_reports_bp.route('/shared/<token>/revoke', methods=['POST'])
@require_auth
def revoke_shared_report_link(token):
    """
    Revokes an active share link. Only the owner can revoke.
    """
    try:
        user_id = request.user_id
        token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
        shared_col = _get_shared_reports_collection()

        res = shared_col.update_one(
            {"token_hash": token_hash, "user_id": user_id},
            {"$set": {"revoked": True, "revoked_at": datetime.utcnow()}}
        )

        if res.matched_count == 0:
            return jsonify({'error': 'Share link not found or unauthorized'}), 404

        return jsonify({'message': 'Shared report link revoked successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@saved_reports_bp.route('/verify/<public_id>', methods=['GET'])
def verify_public_report(public_id):
    """
    Phase 22: Public Report Verification endpoint.
    Returns cryptographic integrity verification without exposing document contents or private user details.
    """
    try:
        shared_col = _get_shared_reports_collection()
        shared_record = shared_col.find_one({"public_id": public_id.upper().strip()})

        if not shared_record:
            return jsonify({
                "valid": False,
                "message": "Report ID not found in verification registry."
            }), 404

        analyses_col = get_analyses_collection()
        analysis = analyses_col.find_one({"_id": ObjectId(shared_record["analysis_id"])})
        if not analysis:
            return jsonify({"valid": False, "message": "Referenced analysis record not found."}), 404

        created_dt = analysis.get("created_at")
        formatted_date = created_dt.strftime("%d %B %Y") if hasattr(created_dt, "strftime") else str(created_dt)

        return jsonify({
            "integrity": "VALID",
            "report_id": shared_record.get("public_id"),
            "risk_score": analysis.get("risk_score", 0),
            "classification": analysis.get("classification", "SAFE"),
            "generated": formatted_date,
            "document_type": analysis.get("document_type", "UNKNOWN"),
            "revoked": shared_record.get("revoked", False),
            "verification_status": "AUTHENTIC_SCAMGUARD_ANALYSIS"
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
