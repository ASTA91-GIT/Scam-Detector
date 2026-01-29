"""
Authentication Blueprint
Handles user signup, login, session management, and profile updates.
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import get_users_collection
from backend.auth_utils import generate_token, require_auth
from datetime import datetime
from bson import ObjectId
import re

# Prefix is handled globally in app.py
auth_bp = Blueprint('auth', __name__)

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

        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        users_collection = get_users_collection()
        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'Email already registered'}), 409

        user_data = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = users_collection.insert_one(user_data)
        token = generate_token(str(result.inserted_id), email)

        return jsonify({
            'message': 'User created successfully',
            'token': token,
            'user': {'id': str(result.inserted_id), 'username': username, 'email': email}
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

        users_collection = get_users_collection()
        user = users_collection.find_one({'email': email})

        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid email or password'}), 401

        token = generate_token(str(user['_id']), email)
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': str(user['_id']), 
                'username': user.get('username'), 
                'email': email
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
            
        return jsonify({
            'username': user.get('username'),
            'email': user.get('email')
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@require_auth
def update_profile():
    try:
        data = request.get_json()
        updated_fields = {}
        if 'username' in data: 
            updated_fields['username'] = data['username'].strip()
        if 'email' in data: 
            updated_fields['email'] = data['email'].strip().lower()
        
        if not updated_fields:
            return jsonify({'error': 'No fields provided'}), 400

        updated_fields['updated_at'] = datetime.utcnow()
        get_users_collection().update_one(
            {'_id': ObjectId(request.user_id)}, 
            {'$set': updated_fields}
        )
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    try:
        data = request.get_json()
        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': ObjectId(request.user_id)})

        if not check_password_hash(user['password'], data.get('old_password')):
            return jsonify({'error': 'Incorrect current password'}), 401

        new_pass = data.get('new_password')
        if not new_pass or len(new_pass) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400

        get_users_collection().update_one(
            {'_id': ObjectId(request.user_id)}, 
            {'$set': {
                'password': generate_password_hash(new_pass), 
                'updated_at': datetime.utcnow()
            }}
        )
        return jsonify({'message': 'Password changed successfully'}), 200
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

        # Consistent with dashboard.js requirement
        return jsonify({
            'username': user.get('username'), 
            'email': user.get('email')
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to load user: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Logged out successfully'}), 200