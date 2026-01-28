"""
Authentication Blueprint
Handles user signup, login, and session management
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import get_users_collection
from backend.auth_utils import generate_token, require_auth
from datetime import datetime
from bson import ObjectId
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# =========================
# SIGNUP
# =========================
@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()

        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()

        if not username:
            return jsonify({'error': 'Username is required'}), 400

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        users_collection = get_users_collection()

        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'Email already registered'}), 409

        hashed_password = generate_password_hash(password)

        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)

        token = generate_token(user_id, email)

        return jsonify({
            'message': 'User created successfully',
            'token': token,
            'user': {
                'id': user_id,
                'username': username,
                'email': email
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
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        users_collection = get_users_collection()
        user = users_collection.find_one({'email': email})

        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid email or password'}), 401

        user_id = str(user['_id'])
        token = generate_token(user_id, email)

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'username': user.get('username'),
                'email': email
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500


# =========================
# PROFILE (✅ NEW)
# =========================
@auth_bp.route('/profile', methods=['GET'])
@require_auth
def profile():
    try:
        user_id = request.user_id
        users_collection = get_users_collection()

        user = users_collection.find_one(
            {'_id': ObjectId(user_id)},
            {'password': 0}
        )

        if not user:
            return jsonify({'error': 'User not found'}), 404

        user['_id'] = str(user['_id'])

        return jsonify({
            'id': user['_id'],
            'username': user.get('username'),
            'email': user.get('email'),
            'created_at': user.get('created_at')
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to load profile: {str(e)}'}), 500


# =========================
# ME
# =========================
@auth_bp.route('/me', methods=['GET'])
@require_auth
def me():
    try:
        user_id = request.user_id
        users_collection = get_users_collection()

        user = users_collection.find_one({'_id': ObjectId(user_id)})

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'name': user.get('username'),
            'email': user.get('email')
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to load user: {str(e)}'}), 500


# =========================
# VERIFY
# =========================
@auth_bp.route('/verify', methods=['GET'])
@require_auth
def verify():
    try:
        user_id = request.user_id
        users_collection = get_users_collection()

        user = users_collection.find_one({'_id': ObjectId(user_id)})

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': {
                'id': str(user['_id']),
                'username': user.get('username'),
                'email': user['email']
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Verification failed: {str(e)}'}), 500


# =========================
# LOGOUT
# =========================
@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Logged out successfully'}), 200
