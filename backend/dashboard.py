"""
Dashboard Blueprint
Aggregates user telemetry, forensic statistics, risk trends,
threat signals, and analysis history filtering.
"""
from flask import Blueprint, request, jsonify
from backend.auth_utils import require_auth
from backend.database import get_analyses_collection, get_saved_reports_collection
from backend.activity_utils import log_activity
from datetime import datetime, timedelta
from bson import ObjectId
import re

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    """Retrieve comprehensive cybersecurity dashboard metrics calculated from real user activity"""
    try:
        user_id = request.user_id
        analyses_collection = get_analyses_collection()
        saved_col = get_saved_reports_collection()

        analyses = list(analyses_collection.find({'user_id': user_id}).sort('created_at', -1))
        saved_count = saved_col.count_documents({'user_id': user_id})

        total = len(analyses)
        safe_count = sum(1 for a in analyses if a.get('risk_level') == 'Safe')
        suspicious_count = sum(1 for a in analyses if a.get('risk_level') == 'Suspicious')
        high_risk_count = sum(1 for a in analyses if a.get('risk_level') in ['High Risk', 'High'])

        avg_trust = round(sum(a.get('trust_score', 0) for a in analyses) / total, 1) if total > 0 else 100.0

        # Safety Score: transparently derived from safe percentage and average trust score
        if total == 0:
            safety_score = 100
            safety_explanation = "Baseline security rating. Run your first analysis to calibrate your safety score."
        else:
            safety_score = round((safe_count * 100 + suspicious_count * 60 + high_risk_count * 10) / total)
            safety_explanation = f"Calculated as the weighted ratio of safe vs high-risk offers across your {total} forensic scans."

        # Risk Trend: aggregate analyses by date (last 7 recorded days or chronological buckets)
        trend_map = {}
        for a in reversed(analyses):  # chronological
            dt = a.get('created_at')
            if dt:
                date_key = dt.strftime('%b %d') if hasattr(dt, 'strftime') else str(dt)[:10]
                if date_key not in trend_map:
                    trend_map[date_key] = {'date': date_key, 'total': 0, 'high_risk': 0, 'safe': 0, 'avg_score': 0, 'scores': []}
                trend_map[date_key]['total'] += 1
                trend_map[date_key]['scores'].append(a.get('trust_score', 0))
                if a.get('risk_level') in ['High Risk', 'High']:
                    trend_map[date_key]['high_risk'] += 1
                elif a.get('risk_level') == 'Safe':
                    trend_map[date_key]['safe'] += 1

        risk_trend = []
        for k, v in trend_map.items():
            v['avg_score'] = round(sum(v['scores']) / len(v['scores']), 1) if v['scores'] else 0
            del v['scores']
            risk_trend.append(v)
        risk_trend = risk_trend[-10:]  # last 10 points

        # Common threat signals identified in user's history
        signal_counts = {}
        for a in analyses:
            # Check structured flags or explanations
            flags = a.get('red_flags', [])
            for f in flags:
                signal_counts[f] = signal_counts.get(f, 0) + 1
            if a.get('email_domain_suspicious'):
                signal_counts["Public / Free Email Domain"] = signal_counts.get("Public / Free Email Domain", 0) + 1
            if a.get('financial_flags_count', 0) > 0:
                signal_counts["Payment / Fee Request"] = signal_counts.get("Payment / Fee Request", 0) + 1
            if a.get('urgency_score', 0) > 1:
                signal_counts["Extreme Urgency Tactics"] = signal_counts.get("Extreme Urgency Tactics", 0) + 1

        top_signals = sorted([{'signal': k, 'count': v} for k, v in signal_counts.items()], key=lambda x: x['count'], reverse=True)[:5]

        return jsonify({
            'total_analyses': total,
            'safe_count': safe_count,
            'suspicious_count': suspicious_count,
            'high_risk_count': high_risk_count,
            'saved_reports_count': saved_count,
            'average_trust_score': avg_trust,
            'safety_score': safety_score,
            'safety_explanation': safety_explanation,
            'risk_trend': risk_trend,
            'top_threat_signals': top_signals
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to retrieve stats: {str(e)}'}), 500


@dashboard_bp.route('/analyses', methods=['GET'])
@require_auth
def get_analyses():
    """Retrieve paginated, searchable, and filtered analyses for current user"""
    try:
        user_id = request.user_id
        analyses_collection = get_analyses_collection()

        limit = max(1, min(100, int(request.args.get('limit', 20))))
        page = max(1, int(request.args.get('page', 1)))
        skip = (page - 1) * limit

        search_query = request.args.get('search', '').strip()
        risk_filter = request.args.get('risk_level', '').strip()
        sort_by = request.args.get('sort', 'newest')

        query = {'user_id': user_id}

        if risk_filter and risk_filter.lower() != 'all':
            if risk_filter.lower() == 'high risk':
                query['risk_level'] = {'$in': ['High Risk', 'High']}
            else:
                query['risk_level'] = risk_filter

        if search_query:
            regex = re.compile(re.escape(search_query), re.IGNORECASE)
            query['$or'] = [
                {'company_name': regex},
                {'job_title': regex},
                {'text': regex},
                {'company_email': regex}
            ]

        # Sorting
        if sort_by == 'oldest':
            sort_field, sort_dir = 'created_at', 1
        elif sort_by == 'score_high':
            sort_field, sort_dir = 'trust_score', -1
        elif sort_by == 'score_low':
            sort_field, sort_dir = 'trust_score', 1
        else:
            sort_field, sort_dir = 'created_at', -1

        total_count = analyses_collection.count_documents(query)
        cursor = analyses_collection.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit)

        analyses = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            doc['analysis_id'] = str(doc['_id'])
            if 'created_at' in doc and hasattr(doc['created_at'], 'isoformat'):
                doc['created_at'] = doc['created_at'].isoformat()
            if 'file_info' in doc and doc['file_info'] and '_id' in doc['file_info']:
                doc['file_info']['_id'] = str(doc['file_info']['_id'])
            analyses.append(doc)

        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

        return jsonify({
            'analyses': analyses,
            'total': total_count,
            'page': page,
            'total_pages': total_pages,
            'limit': limit
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to retrieve analyses: {str(e)}'}), 500


@dashboard_bp.route('/analyses/<analysis_id>', methods=['DELETE'])
@require_auth
def delete_analysis(analysis_id):
    """Delete an individual analysis record"""
    try:
        user_id = request.user_id
        analyses_collection = get_analyses_collection()

        try:
            obj_id = ObjectId(analysis_id)
        except Exception:
            return jsonify({'error': 'Invalid analysis ID'}), 400

        result = analyses_collection.delete_one({'_id': obj_id, 'user_id': user_id})
        if result.deleted_count == 0:
            return jsonify({'error': 'Analysis not found or unauthorized'}), 404

        # Also remove from saved reports if present
        get_saved_reports_collection().delete_many({'analysis_id': analysis_id, 'user_id': user_id})
        log_activity(user_id, "analysis_deleted", f"Deleted scan record #{analysis_id}")

        return jsonify({'message': 'Analysis deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to delete analysis: {str(e)}'}), 500


@dashboard_bp.route('/clear-history', methods=['POST'])
@require_auth
def clear_history():
    """Clear all analysis history for user with confirmation"""
    try:
        user_id = request.user_id
        analyses_collection = get_analyses_collection()
        deleted = analyses_collection.delete_many({'user_id': user_id})

        log_activity(user_id, "history_cleared", f"Cleared all {deleted.deleted_count} scan records")
        return jsonify({'message': f'Successfully cleared {deleted.deleted_count} analysis records'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/summary', methods=['GET'])
@require_auth
def dashboard_summary():
    """Backwards-compatible summary endpoint"""
    return get_stats()
