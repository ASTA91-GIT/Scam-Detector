"""
Notifications Blueprint
Manages user security alerts, analysis completion notifications, and updates
"""
from flask import Blueprint, request, jsonify
from backend.auth_utils import require_auth
from backend.database import get_notifications_collection
from bson import ObjectId

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('', methods=['GET'])
@require_auth
def get_notifications():
    """Retrieve notifications and current unread badge count"""
    try:
        user_id = request.user_id
        col = get_notifications_collection()

        cursor = col.find({'user_id': user_id}).sort('created_at', -1).limit(30)
        notifications = []
        for n in cursor:
            n['_id'] = str(n['_id'])
            if 'created_at' in n and hasattr(n['created_at'], 'isoformat'):
                n['created_at'] = n['created_at'].isoformat()
            notifications.append(n)

        unread_count = col.count_documents({'user_id': user_id, 'read': False})

        return jsonify({
            'notifications': notifications,
            'unread_count': unread_count
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/<notification_id>/read', methods=['POST'])
@require_auth
def mark_read(notification_id):
    """Mark a specific notification as read"""
    try:
        user_id = request.user_id
        try:
            obj_id = ObjectId(notification_id)
        except Exception:
            return jsonify({'error': 'Invalid notification ID'}), 400

        col = get_notifications_collection()
        col.update_one({'_id': obj_id, 'user_id': user_id}, {'$set': {'read': True}})

        unread_count = col.count_documents({'user_id': user_id, 'read': False})
        return jsonify({'message': 'Notification marked as read', 'unread_count': unread_count}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/mark-all-read', methods=['POST'])
@require_auth
def mark_all_read():
    """Mark all notifications as read for current user"""
    try:
        user_id = request.user_id
        col = get_notifications_collection()
        col.update_many({'user_id': user_id, 'read': False}, {'$set': {'read': True}})

        return jsonify({'message': 'All notifications marked as read', 'unread_count': 0}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/clear', methods=['DELETE'])
@require_auth
def clear_notifications():
    """Clear all read notifications"""
    try:
        user_id = request.user_id
        col = get_notifications_collection()
        res = col.delete_many({'user_id': user_id})

        return jsonify({'message': f'Cleared {res.deleted_count} notifications', 'unread_count': 0}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
