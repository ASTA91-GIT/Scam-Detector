"""
Authentication Utilities for ScamGuard AI
JWT token generation, signature verification, session validation,
and role-based access control (RBAC).
"""

import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from bson import ObjectId

SECRET_KEY = os.getenv('JWT_SECRET_KEY') or os.getenv('SECRET_KEY') or 'dev-secret-key-change-in-production'
TOKEN_EXPIRY_HOURS = int(os.getenv('TOKEN_EXPIRY_HOURS', '24'))


def generate_token(user_id: str, email: str, session_id: str = None, role: str = "USER", token_version: int = 1) -> str:
    """Generate cryptographically signed JWT token with session telemetry and versioning."""
    payload = {
        'user_id': str(user_id),
        'email': email,
        'session_id': session_id,
        'role': role or "USER",
        'token_version': token_version,
        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def verify_token(token: str):
    """Verify JWT token signature and expiry."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

decode_token = verify_token


def extract_token_from_request() -> str:
    """Extracts bearer token from Authorization header or fallback header."""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        parts = auth_header.split(' ')
        if len(parts) >= 2:
            return parts[1].strip()
    
    # Fallback headers
    return request.headers.get('X-Auth-Token') or request.args.get('token')


def require_auth(f):
    """Decorator to require valid authentication with session state validation."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_token_from_request()
        if not token:
            return jsonify({
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Authentication required. Please provide a valid Bearer token.'
                }
            }), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({
                'error': {
                    'code': 'INVALID_TOKEN',
                    'message': 'Token has expired or signature is invalid.'
                }
            }), 401
        
        user_id = payload.get('user_id')
        token_version = payload.get('token_version', 1)
        session_id = payload.get('session_id')

        # Validate against database state to support immediate session revocation
        from backend.database import get_users_collection, get_db
        users_col = get_users_collection()
        if users_col is not None:
            try:
                user = users_col.find_one({'_id': ObjectId(user_id)})
                if not user:
                    return jsonify({'error': {'code': 'USER_NOT_FOUND', 'message': 'Account no longer exists.'}}), 401
                
                # Check token version revocation
                if user.get('token_version', 1) > token_version:
                    return jsonify({
                        'error': {'code': 'SESSION_REVOKED', 'message': 'Session has been invalidated due to credential update.'}
                    }), 401

                # Check individual session revocation
                if session_id:
                    db = get_db()
                    session_rec = db.sessions.find_one({'session_id': session_id, 'revoked': True})
                    if session_rec:
                        return jsonify({
                            'error': {'code': 'SESSION_REVOKED', 'message': 'This specific session has been signed out.'}
                        }), 401

                request.user_role = user.get('role', payload.get('role', 'USER'))
            except Exception:
                request.user_role = payload.get('role', 'USER')
        else:
            request.user_role = payload.get('role', 'USER')

        request.user_id = user_id
        request.user_email = payload.get('email')
        request.session_id = session_id
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_admin(f):
    """Decorator to restrict access strictly to users with the ADMIN role."""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        if getattr(request, 'user_role', 'USER') != 'ADMIN':
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Administrative privileges required to access this resource.'
                }
            }), 403
        return f(*args, **kwargs)
    return decorated_function
