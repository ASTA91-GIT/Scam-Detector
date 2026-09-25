"""
Activity Logging and Notification Utilities
Records audit trail and dispatches user notifications
"""
from datetime import datetime
from backend.database import get_activity_logs_collection, get_notifications_collection

def log_activity(user_id, action, details="", ip_address=None):
    """Log an audit action for a user"""
    try:
        col = get_activity_logs_collection()
        entry = {
            'user_id': str(user_id),
            'action': action,
            'details': details,
            'ip': ip_address,
            'created_at': datetime.utcnow()
        }
        col.insert_one(entry)
    except Exception as e:
        print(f"Warning: Failed to log activity: {e}")

def create_notification(user_id, title, message, notif_type='info', link=None):
    """Create an in-app notification for a user"""
    try:
        col = get_notifications_collection()
        entry = {
            'user_id': str(user_id),
            'title': title,
            'message': message,
            'type': notif_type,  # 'info', 'warning', 'danger', 'success'
            'link': link,
            'read': False,
            'created_at': datetime.utcnow()
        }
        col.insert_one(entry)
    except Exception as e:
        print(f"Warning: Failed to create notification: {e}")
