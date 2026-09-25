"""
Authentication and User Management Blueprint
Handles signup, login, session management, profile, avatar uploads,
preferences, security credentials, activity history, and data export.
"""
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from backend.database import (
    get_users_collection, get_analyses_collection, get_files_collection,
    get_saved_reports_collection, get_notifications_collection,
    get_activity_logs_collection, get_preferences_collection
)
from backend.auth_utils import generate_token, require_auth
from backend.activity_utils import log_activity, create_notification
from datetime import datetime
from bson import ObjectId
import os
import re

auth_bp = Blueprint('auth', __name__)

ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_AVATAR_SIZE = 3 * 1024 * 1024  # 3MB

def allowed_avatar_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS

# =========================
# SIGNUP
# =========================
@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()

        if not username or not email or not password:
            return jsonify({'error': 'All fields are required.'}), 400

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Please enter a valid email address.'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long.'}), 400

        users_collection = get_users_collection()
        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'An account with this email already exists.'}), 409

        now = datetime.utcnow()
        user_data = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'avatar_url': None,
            'created_at': now,
            'updated_at': now,
            'last_login': now,
            'token_version': 1
        }

        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        token = generate_token(user_id, email)

        # Set default preferences
        get_preferences_collection().update_one(
            {'user_id': user_id},
            {'$set': {
                'user_id': user_id,
                'theme': 'dark',
                'email_notifications': True,
                'analysis_notifications': True,
                'security_notifications': True,
                'density': 'comfortable',
                'default_mode': 'text',
                'updated_at': now
            }},
            upsert=True
        )

        log_activity(user_id, "account_created", "User registered new cybersecurity analyst account")
        create_notification(
            user_id=user_id,
            title="Welcome to Scam Detector",
            message="Your account is active. Start scanning job offers and offer letters to detect employment fraud.",
            notif_type="info",
            link="analyze.html"
        )

        return jsonify({
            'message': 'Account created successfully',
            'token': token,
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'avatar_url': None
            }
        }), 201
    except Exception as e:
        return jsonify({'error': f'Signup failed: {str(e)}'}), 500

# =========================
# LOGIN
# =========================
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()

        if not email or not password:
            return jsonify({'error': 'Email and password are required.'}), 400

        users_collection = get_users_collection()
        user = users_collection.find_one({'email': email})

        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid email or password.'}), 401

        user_id = str(user['_id'])
        now = datetime.utcnow()
        users_collection.update_one({'_id': user['_id']}, {'$set': {'last_login': now}})

        token = generate_token(user_id, email)
        log_activity(user_id, "login", "User successfully authenticated into workspace")

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'username': user.get('username'),
                'email': email,
                'avatar_url': user.get('avatar_url')
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

# =========================
# PROFILE MANAGEMENT
# =========================
@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    try:
        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        analyses_count = get_analyses_collection().count_documents({'user_id': request.user_id})
        saved_count = get_saved_reports_collection().count_documents({'user_id': request.user_id})
        high_risk_count = get_analyses_collection().count_documents({
            'user_id': request.user_id,
            'risk_level': {'$in': ['High Risk', 'High']}
        })

        return jsonify({
            'id': str(user['_id']),
            'username': user.get('username', 'Analyst'),
            'email': user.get('email'),
            'avatar_url': user.get('avatar_url'),
            'created_at': user.get('created_at').isoformat() if user.get('created_at') else None,
            'last_login': user.get('last_login').isoformat() if user.get('last_login') else None,
            'stats': {
                'total_analyses': analyses_count,
                'saved_reports': saved_count,
                'high_risk_detected': high_risk_count
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/profile', methods=['PUT'])
@require_auth
def update_profile():
    try:
        data = request.get_json() or {}
        updated_fields = {}
        if 'username' in data and data['username'].strip():
            updated_fields['username'] = data['username'].strip()
        if 'email' in data and data['email'].strip():
            new_email = data['email'].strip().lower()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, new_email):
                return jsonify({'error': 'Invalid email format'}), 400

            # Check if email taken by someone else
            existing = get_users_collection().find_one({'email': new_email, '_id': {'$ne': ObjectId(request.user_id)}})
            if existing:
                return jsonify({'error': 'Email is already in use by another account'}), 409
            updated_fields['email'] = new_email

        if not updated_fields:
            return jsonify({'error': 'No fields provided for update'}), 400

        updated_fields['updated_at'] = datetime.utcnow()
        get_users_collection().update_one(
            {'_id': ObjectId(request.user_id)},
            {'$set': updated_fields}
        )

        log_activity(request.user_id, "profile_updated", f"Updated account information: {', '.join(updated_fields.keys())}")
        create_notification(
            user_id=request.user_id,
            title="Profile Updated",
            message="Your account profile information has been successfully saved.",
            notif_type="info"
        )

        return jsonify({'message': 'Profile updated successfully', 'user': updated_fields}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================
# AVATAR MANAGEMENT
# =========================
@auth_bp.route('/avatar', methods=['POST'])
@require_auth
def upload_avatar():
    try:
        if 'avatar' not in request.files:
            return jsonify({'error': 'No avatar file provided'}), 400

        file = request.files['avatar']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not allowed_avatar_file(file.filename):
            return jsonify({'error': 'Invalid file format. Allowed: PNG, JPG, JPEG, WEBP'}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"avatar_{request.user_id}_{int(datetime.utcnow().timestamp())}.{ext}")

        avatar_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
        os.makedirs(avatar_folder, exist_ok=True)
        file_path = os.path.join(avatar_folder, filename)
        file.save(file_path)

        avatar_url = f"/api/auth/avatar/{filename}"

        get_users_collection().update_one(
            {'_id': ObjectId(request.user_id)},
            {'$set': {'avatar_url': avatar_url, 'updated_at': datetime.utcnow()}}
        )

        log_activity(request.user_id, "avatar_uploaded", "User updated profile avatar")
        return jsonify({'message': 'Avatar uploaded successfully', 'avatar_url': avatar_url}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/avatar/<filename>', methods=['GET'])
def get_avatar(filename):
    """Serve uploaded avatar securely"""
    avatar_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
    return send_from_directory(avatar_folder, secure_filename(filename))


@auth_bp.route('/avatar', methods=['DELETE'])
@require_auth
def remove_avatar():
    try:
        get_users_collection().update_one(
            {'_id': ObjectId(request.user_id)},
            {'$set': {'avatar_url': None, 'updated_at': datetime.utcnow()}}
        )
        log_activity(request.user_id, "avatar_removed", "User reverted to initial-based avatar")
        return jsonify({'message': 'Avatar removed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================
# CHANGE PASSWORD
# =========================
@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    try:
        data = request.get_json() or {}
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()

        if not old_password or not new_password:
            return jsonify({'error': 'Current and new password are required.'}), 400

        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        if not user or not check_password_hash(user['password'], old_password):
            return jsonify({'error': 'Incorrect current password.'}), 401

        # Security policy: min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters long.'}), 400
        if not re.search(r'[A-Z]', new_password):
            return jsonify({'error': 'Password must contain at least one uppercase letter.'}), 400
        if not re.search(r'[a-z]', new_password):
            return jsonify({'error': 'Password must contain at least one lowercase letter.'}), 400
        if not re.search(r'\d', new_password):
            return jsonify({'error': 'Password must contain at least one number.'}), 400
        if not re.search(r'[@$!%*?&#^()_+\-=\[\]{};:\'",.<>\/]', new_password):
            return jsonify({'error': 'Password must contain at least one special character.'}), 400

        users_collection.update_one(
            {'_id': ObjectId(request.user_id)},
            {'$set': {
                'password': generate_password_hash(new_password),
                'updated_at': datetime.utcnow()
            }}
        )

        log_activity(request.user_id, "password_changed", "User credentials updated successfully")
        create_notification(
            user_id=request.user_id,
            title="Password Changed",
            message="Your account password was updated. If you did not make this change, contact support immediately.",
            notif_type="warning"
        )

        return jsonify({'message': 'Password changed successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================
# USER PREFERENCES
# =========================
@auth_bp.route('/preferences', methods=['GET'])
@require_auth
def get_preferences():
    try:
        col = get_preferences_collection()
        prefs = col.find_one({'user_id': request.user_id})
        if not prefs:
            return jsonify({
                'theme': 'dark',
                'email_notifications': True,
                'analysis_notifications': True,
                'security_notifications': True,
                'density': 'comfortable',
                'default_mode': 'text'
            }), 200

        prefs['_id'] = str(prefs['_id'])
        return jsonify(prefs), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/preferences', methods=['PUT'])
@require_auth
def update_preferences():
    try:
        data = request.get_json() or {}
        allowed_keys = ['theme', 'email_notifications', 'analysis_notifications', 'security_notifications', 'density', 'default_mode']
        updates = {k: data[k] for k in allowed_keys if k in data}
        updates['updated_at'] = datetime.utcnow()

        col = get_preferences_collection()
        col.update_one({'user_id': request.user_id}, {'$set': updates}, upsert=True)

        return jsonify({'message': 'Preferences saved successfully', 'preferences': updates}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================
# AUDIT ACTIVITY LOG
# =========================
@auth_bp.route('/activity', methods=['GET'])
@require_auth
def get_activity():
    try:
        col = get_activity_logs_collection()
        logs_cursor = col.find({'user_id': request.user_id}).sort('created_at', -1).limit(50)
        logs = []
        for entry in logs_cursor:
            entry['_id'] = str(entry['_id'])
            if 'created_at' in entry and hasattr(entry['created_at'], 'isoformat'):
                entry['created_at'] = entry['created_at'].isoformat()
            logs.append(entry)
        return jsonify({'activity': logs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================
# DATA EXPORT & DANGER ZONE
# =========================
@auth_bp.route('/export-data', methods=['GET'])
@require_auth
def export_data():
    """Generates complete GDPR/Privacy data export for user"""
    try:
        user_id = request.user_id
        user = get_users_collection().find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        analyses = list(get_analyses_collection().find({'user_id': user_id}))
        for a in analyses:
            a['_id'] = str(a['_id'])
            if 'created_at' in a and hasattr(a['created_at'], 'isoformat'):
                a['created_at'] = a['created_at'].isoformat()

        saved = list(get_saved_reports_collection().find({'user_id': user_id}))
        for s in saved:
            s['_id'] = str(s['_id'])
            if 'created_at' in s and hasattr(s['created_at'], 'isoformat'):
                s['created_at'] = s['created_at'].isoformat()

        activity = list(get_activity_logs_collection().find({'user_id': user_id}))
        for act in activity:
            act['_id'] = str(act['_id'])
            if 'created_at' in act and hasattr(act['created_at'], 'isoformat'):
                act['created_at'] = act['created_at'].isoformat()

        preferences = get_preferences_collection().find_one({'user_id': user_id})
        if preferences:
            preferences['_id'] = str(preferences['_id'])

        export_payload = {
            'account': {
                'id': str(user['_id']),
                'username': user.get('username'),
                'email': user.get('email'),
                'created_at': user.get('created_at').isoformat() if user.get('created_at') else None,
                'last_login': user.get('last_login').isoformat() if user.get('last_login') else None
            },
            'preferences': preferences,
            'analyses_count': len(analyses),
            'analyses': analyses,
            'saved_reports': saved,
            'activity_logs': activity,
            'exported_at': datetime.utcnow().isoformat()
        }

        log_activity(user_id, "data_exported", "User exported full personal cybersecurity archive")
        return jsonify(export_payload), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/delete-account', methods=['POST'])
@require_auth
def delete_account():
    """Permanently delete user and cascade delete all associated records"""
    try:
        data = request.get_json() or {}
        password = data.get('password', '').strip()

        if not password:
            return jsonify({'error': 'Password is required to confirm account deletion.'}), 400

        user_id = request.user_id
        users_col = get_users_collection()
        user = users_col.find_one({'_id': ObjectId(user_id)})

        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Incorrect password. Account deletion aborted.'}), 401

        # Cascade delete
        get_analyses_collection().delete_many({'user_id': user_id})
        get_saved_reports_collection().delete_many({'user_id': user_id})
        get_notifications_collection().delete_many({'user_id': user_id})
        get_activity_logs_collection().delete_many({'user_id': user_id})
        get_preferences_collection().delete_one({'user_id': user_id})
        get_files_collection().delete_many({'user_id': user_id})
        users_col.delete_one({'_id': ObjectId(user_id)})

        return jsonify({'message': 'Account and all associated records permanently deleted.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================
# SESSION HELPERS
# =========================
@auth_bp.route('/me', methods=['GET'])
@require_auth
def me():
    try:
        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'id': str(user['_id']),
            'username': user.get('username'),
            'email': user.get('email'),
            'avatar_url': user.get('avatar_url')
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to load user: {str(e)}'}), 500


@auth_bp.route('/logout-all', methods=['POST'])
@require_auth
def logout_all():
    try:
        # Increment token_version to invalidate tokens if tracked
        get_users_collection().update_one(
            {'_id': ObjectId(request.user_id)},
            {'$inc': {'token_version': 1}, '$set': {'updated_at': datetime.utcnow()}}
        )
        log_activity(request.user_id, "logout_all_sessions", "Terminated all active device sessions")
        return jsonify({'message': 'Successfully logged out from all active sessions.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Logged out successfully'}), 200