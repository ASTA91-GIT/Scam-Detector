"""
Authentication, User Lifecycle, and Security Blueprint for ScamGuard AI
Handles:
- User signup with cryptographic email verification
- Rate-limited login with session telemetry and device fingerprinting
- Password reset flow with single-use hashed tokens
- Active session management and selective revocation
- Email notification preferences
- Security alerts dispatch via Node.js mailer
- Account privacy and data deletion
"""

import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson import ObjectId

from backend.database import (
    get_users_collection, get_analyses_collection, get_files_collection,
    get_saved_reports_collection, get_notifications_collection,
    get_activity_logs_collection, get_preferences_collection, get_db
)
from backend.auth_utils import generate_token, require_auth, require_admin
from backend.activity_utils import log_activity, create_notification
from backend.audit_logger import log_audit_event
from backend.session_utils import create_session_record, parse_user_agent, get_client_ip
from backend.rate_limiter import rate_limit
from backend.mail_client import send_email

auth_bp = Blueprint('auth', __name__)

ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5000')


def allowed_avatar_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a raw token."""
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


# ==============================================================================
# SIGNUP & REGISTRATION
# ==============================================================================
@auth_bp.route('/signup', methods=['POST'])
@rate_limit(limit=5, window_seconds=3600, bucket='register')
def signup():
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()

        if not username or not email or not password:
            return jsonify({'error': {'code': 'MISSING_FIELDS', 'message': 'Username, email, and password are required.'}}), 400

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': {'code': 'INVALID_EMAIL', 'message': 'Please enter a valid email address.'}}), 400

        if len(password) < 8:
            return jsonify({'error': {'code': 'WEAK_PASSWORD', 'message': 'Password must be at least 8 characters long.'}}), 400

        users_collection = get_users_collection()
        if users_collection.find_one({'email': email}):
            return jsonify({'error': {'code': 'EMAIL_EXISTS', 'message': 'An account with this email already exists.'}}), 409

        now = datetime.utcnow()
        raw_verification_token = secrets.token_urlsafe(32)
        verification_hash = hash_token(raw_verification_token)
        verification_expires = now + timedelta(hours=24)

        user_data = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'role': 'USER',
            'avatar_url': None,
            'email_verified': False,
            'verification_token_hash': verification_hash,
            'verification_token_expires': verification_expires,
            'verified_at': None,
            'notification_preferences': {
                'analysis_completed': True,
                'high_risk_alerts': True,
                'security_alerts': True,
                'product_updates': False
            },
            'created_at': now,
            'updated_at': now,
            'last_login': now,
            'token_version': 1
        }

        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)

        # Create initial active session
        session_rec = create_session_record(user_id)
        db = get_db()
        if db is not None:
            db.sessions.insert_one(session_rec)

        token = generate_token(user_id, email, session_id=session_rec['session_id'], role='USER', token_version=1)

        # Initialize preferences
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
        log_audit_event("USER_REGISTERED", user_id=user_id, email=email)

        create_notification(
            user_id=user_id,
            title="Welcome to ScamGuard AI",
            message="Your account is active. Please verify your email to unlock all intelligence features.",
            notif_type="info",
            link="settings.html"
        )

        # Dispatch welcome & verification emails
        verification_url = f"{FRONTEND_URL}/verify.html?token={raw_verification_token}"
        send_email(
            to=email,
            template="welcome",
            data={
                "username": username,
                "login_url": f"{FRONTEND_URL}/login.html"
            }
        )
        send_email(
            to=email,
            template="verify-email",
            data={
                "verification_url": verification_url,
                "expires_in_hours": 24
            }
        )

        return jsonify({
            'message': 'Account created successfully. A verification link has been sent to your email.',
            'token': token,
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'role': 'USER',
                'email_verified': False,
                'avatar_url': None
            }
        }), 201
    except Exception as e:
        return jsonify({'error': {'code': 'SIGNUP_FAILED', 'message': f'Signup failed: {str(e)}'}}), 500


# ==============================================================================
# EMAIL VERIFICATION
# ==============================================================================
@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Validates email verification token and marks account verified."""
    try:
        token = request.args.get('token')
        if not token and request.is_json:
            token = (request.get_json() or {}).get('token')

        if not token:
            return jsonify({'error': {'code': 'INVALID_TOKEN', 'message': 'Verification token is required.'}}), 400

        token_hash = hash_token(token)
        now = datetime.utcnow()

        users_col = get_users_collection()
        user = users_col.find_one({
            'verification_token_hash': token_hash,
            'verification_token_expires': {'$gt': now}
        })

        if not user:
            return jsonify({
                'error': {
                    'code': 'EXPIRED_OR_INVALID_TOKEN',
                    'message': 'Verification token is invalid, expired, or already used.'
                }
            }), 400

        user_id = str(user['_id'])
        users_col.update_one(
            {'_id': user['_id']},
            {'$set': {
                'email_verified': True,
                'verified_at': now,
                'verification_token_hash': None,
                'verification_token_expires': None,
                'updated_at': now
            }}
        )

        log_audit_event("EMAIL_VERIFIED", user_id=user_id, email=user.get('email'))
        log_activity(user_id, "email_verified", "User successfully verified email address")

        create_notification(
            user_id=user_id,
            title="Email Verified",
            message="Your email address has been verified. Full forensic capabilities enabled.",
            notif_type="success"
        )

        return jsonify({
            'message': 'Email successfully verified.',
            'verified': True
        }), 200
    except Exception as e:
        return jsonify({'error': {'code': 'VERIFICATION_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/resend-verification', methods=['POST'])
@rate_limit(limit=5, window_seconds=300, bucket='resend_verification')
def resend_verification():
    """Generates a fresh single-use verification token and dispatches email."""
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()

        # If authenticated, fall back to user's email
        if not email and hasattr(request, 'user_email') and request.user_email:
            email = request.user_email

        if not email:
            return jsonify({'error': {'code': 'MISSING_EMAIL', 'message': 'Email is required.'}}), 400

        users_col = get_users_collection()
        user = users_col.find_one({'email': email})

        # Generic response to prevent enumeration
        generic_msg = "If an unverified account exists for this email, a verification link has been sent."

        if not user:
            return jsonify({'message': generic_msg}), 200

        if user.get('email_verified', False):
            return jsonify({'message': 'This email address is already verified.'}), 200

        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_token(raw_token)
        now = datetime.utcnow()

        users_col.update_one(
            {'_id': user['_id']},
            {'$set': {
                'verification_token_hash': token_hash,
                'verification_token_expires': now + timedelta(hours=24),
                'updated_at': now
            }}
        )

        verification_url = f"{FRONTEND_URL}/verify.html?token={raw_token}"
        send_email(
            to=email,
            template="verify-email",
            data={
                "verification_url": verification_url,
                "expires_in_hours": 24
            }
        )

        return jsonify({'message': generic_msg}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'RESEND_FAILED', 'message': str(e)}}), 500


# ==============================================================================
# LOGIN & SESSIONS
# ==============================================================================
@auth_bp.route('/login', methods=['POST'])
@rate_limit(limit=10, window_seconds=900, bucket='login')
def login():
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()

        if not email or not password:
            return jsonify({'error': {'code': 'MISSING_CREDENTIALS', 'message': 'Email and password are required.'}}), 400

        users_collection = get_users_collection()
        user = users_collection.find_one({'email': email})

        if not user or not check_password_hash(user['password'], password):
            log_audit_event("LOGIN_FAILED", email=email, status="FAILED")
            return jsonify({'error': {'code': 'INVALID_CREDENTIALS', 'message': 'Invalid email or password.'}}), 401

        user_id = str(user['_id'])
        now = datetime.utcnow()
        users_collection.update_one({'_id': user['_id']}, {'$set': {'last_login': now}})

        # Record active session
        session_rec = create_session_record(user_id)
        db = get_db()
        if db is not None:
            db.sessions.insert_one(session_rec)

        token_version = user.get('token_version', 1)
        role = user.get('role', 'USER')
        token = generate_token(user_id, email, session_id=session_rec['session_id'], role=role, token_version=token_version)

        log_activity(user_id, "login", f"Authenticated from {session_rec['device']} ({session_rec['ip_address']})")
        log_audit_event("LOGIN_SUCCESS", user_id=user_id, email=email, metadata={
            "device": session_rec['device'],
            "ip": session_rec['ip_address']
        })

        # Send security notification if enabled in preferences
        prefs = user.get('notification_preferences', {})
        if prefs.get('security_alerts', True):
            send_email(
                to=email,
                template="security-alert",
                subject="Security Alert: New Sign-in to ScamGuard AI",
                data={
                    "alert_title": "New Sign-in Detected",
                    "alert_description": "A successful authentication was recorded on your cybersecurity analyst account.",
                    "event_type": "LOGIN_SUCCESS",
                    "timestamp": now.strftime("%d %b %Y, %I:%M %p UTC"),
                    "ip_address": session_rec['ip_address'],
                    "browser": session_rec['browser'],
                    "os": session_rec['os'],
                    "security_center_url": f"{FRONTEND_URL}/settings.html#security"
                }
            )

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'username': user.get('username'),
                'email': email,
                'role': role,
                'email_verified': user.get('email_verified', False),
                'avatar_url': user.get('avatar_url')
            }
        }), 200
    except Exception as e:
        return jsonify({'error': {'code': 'LOGIN_FAILED', 'message': f'Login failed: {str(e)}'}}), 500


# ==============================================================================
# PASSWORD RESET (FORGOT / RESET)
# ==============================================================================
@auth_bp.route('/forgot-password', methods=['POST'])
@rate_limit(limit=5, window_seconds=3600, bucket='forgot_password')
def forgot_password():
    """Generates password reset token and dispatches secure link."""
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()

        generic_response = {
            'message': 'If an account exists for this email, a password reset link has been sent.'
        }

        if not email:
            return jsonify({'error': {'code': 'MISSING_EMAIL', 'message': 'Email address is required.'}}), 400

        users_col = get_users_collection()
        user = users_col.find_one({'email': email})

        if not user:
            return jsonify(generic_response), 200

        raw_reset_token = secrets.token_urlsafe(32)
        reset_hash = hash_token(raw_reset_token)
        now = datetime.utcnow()
        expires = now + timedelta(minutes=30)

        users_col.update_one(
            {'_id': user['_id']},
            {'$set': {
                'reset_token_hash': reset_hash,
                'reset_token_expires': expires,
                'updated_at': now
            }}
        )

        user_id = str(user['_id'])
        log_audit_event("PASSWORD_RESET_REQUESTED", user_id=user_id, email=email)

        reset_url = f"{FRONTEND_URL}/reset.html?token={raw_reset_token}"
        send_email(
            to=email,
            template="password-reset",
            data={
                "reset_url": reset_url,
                "expires_in_minutes": 30
            }
        )

        return jsonify(generic_response), 200
    except Exception as e:
        return jsonify({'error': {'code': 'FORGOT_PASSWORD_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/reset-password', methods=['POST'])
@rate_limit(limit=10, window_seconds=3600, bucket='reset_password')
def reset_password():
    """Validates single-use reset token and updates account credentials."""
    try:
        data = request.get_json() or {}
        token = data.get('token', '').strip()
        new_password = data.get('new_password', '').strip()

        if not token or not new_password:
            return jsonify({'error': {'code': 'MISSING_FIELDS', 'message': 'Token and new password are required.'}}), 400

        if len(new_password) < 8:
            return jsonify({'error': {'code': 'WEAK_PASSWORD', 'message': 'Password must be at least 8 characters long.'}}), 400

        token_hash = hash_token(token)
        now = datetime.utcnow()

        users_col = get_users_collection()
        user = users_col.find_one({
            'reset_token_hash': token_hash,
            'reset_token_expires': {'$gt': now}
        })

        if not user:
            return jsonify({
                'error': {
                    'code': 'INVALID_OR_EXPIRED_TOKEN',
                    'message': 'Password reset link is invalid or has expired.'
                }
            }), 400

        user_id = str(user['_id'])
        db = get_db()

        # Update password, invalidate reset token, increment token version, revoke sessions
        users_col.update_one(
            {'_id': user['_id']},
            {
                '$set': {
                    'password': generate_password_hash(new_password),
                    'reset_token_hash': None,
                    'reset_token_expires': None,
                    'updated_at': now
                },
                '$inc': {'token_version': 1}
            }
        )

        if db is not None:
            db.sessions.update_many({'user_id': user_id}, {'$set': {'revoked': True}})

        log_audit_event("PASSWORD_CHANGED", user_id=user_id, email=user.get('email'))
        log_activity(user_id, "password_reset", "Password was reset via single-use email verification token")

        # Security alert email
        send_email(
            to=user.get('email'),
            template="security-alert",
            subject="Security Alert: Password Changed",
            data={
                "alert_title": "Password Changed Successfully",
                "alert_description": "Your account password was updated. All other active sessions have been invalidated.",
                "event_type": "PASSWORD_CHANGED",
                "timestamp": now.strftime("%d %b %Y, %I:%M %p UTC"),
                "ip_address": get_client_ip(),
                "browser": parse_user_agent(request.headers.get("User-Agent"))["browser"],
                "os": parse_user_agent(request.headers.get("User-Agent"))["os"],
                "security_center_url": f"{FRONTEND_URL}/settings.html#security"
            }
        )

        return jsonify({'message': 'Password has been successfully reset. Please log in with your new password.'}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'RESET_FAILED', 'message': str(e)}}), 500


# ==============================================================================
# SESSION MANAGEMENT (PHASE 9)
# ==============================================================================
@auth_bp.route('/sessions', methods=['GET'])
@require_auth
def get_active_sessions():
    """Lists all active and historical sessions for current user."""
    try:
        db = get_db()
        sessions = []
        if db is not None:
            cur = db.sessions.find({'user_id': request.user_id, 'revoked': False}).sort('last_seen', -1).limit(20)
            for s in cur:
                sessions.append({
                    'session_id': s.get('session_id'),
                    'ip_address': s.get('ip_address'),
                    'device': s.get('device', 'Unknown Device'),
                    'browser': s.get('browser', 'Browser'),
                    'os': s.get('os', 'OS'),
                    'created_at': s.get('created_at').isoformat() if s.get('created_at') else None,
                    'last_seen': s.get('last_seen').isoformat() if s.get('last_seen') else None,
                    'is_current': s.get('session_id') == getattr(request, 'session_id', None)
                })

        return jsonify({'sessions': sessions}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'SESSION_FETCH_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/sessions/revoke-others', methods=['POST'])
@require_auth
def revoke_other_sessions():
    """Revokes all sessions for user except current session."""
    try:
        db = get_db()
        current_sess_id = getattr(request, 'session_id', None)

        if db is not None:
            filter_q = {'user_id': request.user_id}
            if current_sess_id:
                filter_q['session_id'] = {'$ne': current_sess_id}
            db.sessions.update_many(filter_q, {'$set': {'revoked': True}})

        log_activity(request.user_id, "revoke_other_sessions", "Signed out of all other remote device sessions")
        log_audit_event("SESSION_REVOKED", user_id=request.user_id, email=request.user_email)

        return jsonify({'message': 'All other active sessions have been revoked.'}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'REVOCATION_FAILED', 'message': str(e)}}), 500


@auth_bp.route('/sessions/revoke/<session_id>', methods=['POST'])
@require_auth
def revoke_session(session_id):
    """Revokes a specific session."""
    try:
        db = get_db()
        if db is not None:
            db.sessions.update_one({'session_id': session_id, 'user_id': request.user_id}, {'$set': {'revoked': True}})
        return jsonify({'message': f'Session {session_id} has been revoked.'}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'REVOCATION_FAILED', 'message': str(e)}}), 500


# ==============================================================================
# NOTIFICATION PREFERENCES (PHASE 8)
# ==============================================================================
@auth_bp.route('/notification-preferences', methods=['GET'])
@require_auth
def get_notification_preferences():
    try:
        users_col = get_users_collection()
        user = users_col.find_one({'_id': ObjectId(request.user_id)})
        prefs = (user or {}).get('notification_preferences', {
            'analysis_completed': True,
            'high_risk_alerts': True,
            'security_alerts': True,
            'product_updates': False
        })
        return jsonify({'notification_preferences': prefs}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'PREFERENCES_FETCH_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/notification-preferences', methods=['PUT'])
@require_auth
def update_notification_preferences():
    try:
        data = request.get_json() or {}
        allowed = ['analysis_completed', 'high_risk_alerts', 'security_alerts', 'product_updates']
        updated = {k: bool(data[k]) for k in allowed if k in data}

        users_col = get_users_collection()
        users_col.update_one(
            {'_id': ObjectId(request.user_id)},
            {'$set': {f'notification_preferences.{k}': v for k, v in updated.items()}}
        )

        return jsonify({'message': 'Notification preferences updated.', 'notification_preferences': updated}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'PREFERENCES_UPDATE_ERROR', 'message': str(e)}}), 500


# ==============================================================================
# PROFILE & SETTINGS
# ==============================================================================
@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    try:
        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        if not user:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404

        analyses_count = get_analyses_collection().count_documents({'user_id': request.user_id})
        saved_count = get_saved_reports_collection().count_documents({'user_id': request.user_id})
        high_risk_count = get_analyses_collection().count_documents({
            'user_id': request.user_id,
            'risk_level': {'$in': ['High Risk', 'High', 'HIGH_RISK']}
        })

        return jsonify({
            'id': str(user['_id']),
            'username': user.get('username', 'Analyst'),
            'email': user.get('email'),
            'role': user.get('role', 'USER'),
            'email_verified': user.get('email_verified', False),
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
        return jsonify({'error': {'code': 'PROFILE_ERROR', 'message': str(e)}}), 500


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
                return jsonify({'error': {'code': 'INVALID_EMAIL', 'message': 'Invalid email format'}}), 400

            existing = get_users_collection().find_one({'email': new_email, '_id': {'$ne': ObjectId(request.user_id)}})
            if existing:
                return jsonify({'error': {'code': 'EMAIL_EXISTS', 'message': 'Email is already in use by another account'}}), 409
            
            updated_fields['email'] = new_email
            updated_fields['email_verified'] = False  # Re-require verification if email changed

        if not updated_fields:
            return jsonify({'error': {'code': 'EMPTY_PAYLOAD', 'message': 'No fields provided for update'}}), 400

        updated_fields['updated_at'] = datetime.utcnow()
        get_users_collection().update_one(
            {'_id': ObjectId(request.user_id)},
            {'$set': updated_fields}
        )

        log_activity(request.user_id, "profile_updated", f"Updated account information: {', '.join(updated_fields.keys())}")
        return jsonify({'message': 'Profile updated successfully', 'user': updated_fields}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'UPDATE_FAILED', 'message': str(e)}}), 500


@auth_bp.route('/avatar', methods=['POST'])
@require_auth
def upload_avatar():
    try:
        if 'avatar' not in request.files:
            return jsonify({'error': {'code': 'MISSING_FILE', 'message': 'No avatar file provided'}}), 400

        file = request.files['avatar']
        if file.filename == '':
            return jsonify({'error': {'code': 'MISSING_FILE', 'message': 'No selected file'}}), 400

        if not allowed_avatar_file(file.filename):
            return jsonify({'error': {'code': 'INVALID_FILE_TYPE', 'message': 'Invalid file format. Allowed: PNG, JPG, JPEG, WEBP'}}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"avatar_{request.user_id}_{secrets.token_hex(8)}.{ext}")

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
        return jsonify({'error': {'code': 'AVATAR_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/avatar/<filename>', methods=['GET'])
def get_avatar(filename):
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
        return jsonify({'message': 'Avatar removed successfully'}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'AVATAR_DELETE_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    try:
        data = request.get_json() or {}
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()

        if not old_password or not new_password:
            return jsonify({'error': {'code': 'MISSING_FIELDS', 'message': 'Current and new password are required.'}}), 400

        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        if not user or not check_password_hash(user['password'], old_password):
            return jsonify({'error': {'code': 'INCORRECT_PASSWORD', 'message': 'Incorrect current password.'}}), 401

        if len(new_password) < 8:
            return jsonify({'error': {'code': 'WEAK_PASSWORD', 'message': 'New password must be at least 8 characters long.'}}), 400

        now = datetime.utcnow()
        users_collection.update_one(
            {'_id': ObjectId(request.user_id)},
            {
                '$set': {
                    'password': generate_password_hash(new_password),
                    'updated_at': now
                },
                '$inc': {'token_version': 1}
            }
        )

        log_activity(request.user_id, "password_changed", "User credentials updated successfully")
        log_audit_event("PASSWORD_CHANGED", user_id=request.user_id, email=user.get('email'))

        # Security alert email
        send_email(
            to=user.get('email'),
            template="security-alert",
            subject="Security Alert: Password Changed",
            data={
                "alert_title": "Password Changed Successfully",
                "alert_description": "Your account password was updated from the settings center.",
                "event_type": "PASSWORD_CHANGED",
                "timestamp": now.strftime("%d %b %Y, %I:%M %p UTC"),
                "ip_address": get_client_ip(),
                "browser": parse_user_agent(request.headers.get("User-Agent"))["browser"],
                "os": parse_user_agent(request.headers.get("User-Agent"))["os"],
                "security_center_url": f"{FRONTEND_URL}/settings.html#security"
            }
        )

        return jsonify({'message': 'Password changed successfully.'}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'CHANGE_PASSWORD_ERROR', 'message': str(e)}}), 500


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
        return jsonify({'error': {'code': 'PREFERENCES_ERROR', 'message': str(e)}}), 500


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
        return jsonify({'error': {'code': 'PREFERENCES_UPDATE_ERROR', 'message': str(e)}}), 500


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
        return jsonify({'error': {'code': 'ACTIVITY_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/delete-account', methods=['POST'])
@auth_bp.route('/me', methods=['DELETE'])
@require_auth
def delete_account():
    """Permanently deletes user, associated analyses, files, and dispatches confirmation."""
    try:
        data = request.get_json() or {}
        password = data.get('password', '').strip()

        if not password:
            return jsonify({'error': {'code': 'PASSWORD_REQUIRED', 'message': 'Password is required to confirm account deletion.'}}), 400

        user_id = request.user_id
        users_col = get_users_collection()
        user = users_col.find_one({'_id': ObjectId(user_id)})

        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': {'code': 'INVALID_PASSWORD', 'message': 'Incorrect password. Account deletion aborted.'}}), 401

        now = datetime.utcnow()
        user_email = user.get('email')

        # Cascade delete
        get_analyses_collection().delete_many({'user_id': user_id})
        get_saved_reports_collection().delete_many({'user_id': user_id})
        get_notifications_collection().delete_many({'user_id': user_id})
        get_activity_logs_collection().delete_many({'user_id': user_id})
        get_preferences_collection().delete_one({'user_id': user_id})
        get_files_collection().delete_many({'user_id': user_id})
        
        db = get_db()
        if db is not None:
            db.sessions.delete_many({'user_id': user_id})
            db.case_chat_messages.delete_many({'user_id': user_id})
            db.case_memory.delete_many({'user_id': user_id})

        users_col.delete_one({'_id': ObjectId(user_id)})

        log_audit_event("ACCOUNT_DELETED", user_id=user_id, email=user_email)

        # Dispatch account deletion receipt email
        if user_email:
            send_email(
                to=user_email,
                template="account-deleted",
                data={"deleted_at": now.strftime("%d %b %Y, %I:%M %p UTC")}
            )

        return jsonify({'message': 'Account and all associated records permanently purged.'}), 200

    except Exception as e:
        return jsonify({'error': {'code': 'DELETE_FAILED', 'message': str(e)}}), 500


@auth_bp.route('/me', methods=['GET'])
@require_auth
def me():
    try:
        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})
        if not user:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404

        return jsonify({
            'id': str(user['_id']),
            'username': user.get('username'),
            'email': user.get('email'),
            'role': user.get('role', 'USER'),
            'email_verified': user.get('email_verified', False),
            'avatar_url': user.get('avatar_url')
        }), 200
    except Exception as e:
        return jsonify({'error': {'code': 'USER_FETCH_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/logout-all', methods=['POST'])
@require_auth
def logout_all():
    try:
        db = get_db()
        if db is not None:
            db.sessions.update_many({'user_id': request.user_id}, {'$set': {'revoked': True}})
        
        get_users_collection().update_one(
            {'_id': ObjectId(request.user_id)},
            {'$inc': {'token_version': 1}, '$set': {'updated_at': datetime.utcnow()}}
        )
        log_activity(request.user_id, "logout_all_sessions", "Terminated all active device sessions")
        log_audit_event("SESSION_REVOKED", user_id=request.user_id, email=request.user_email)
        return jsonify({'message': 'Successfully logged out from all active sessions.'}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'LOGOUT_ALL_FAILED', 'message': str(e)}}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Logged out successfully'}), 200