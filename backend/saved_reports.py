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
