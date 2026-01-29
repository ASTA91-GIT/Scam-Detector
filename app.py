"""
Main Flask Application
AI-Powered Job & Internship Scam Detector
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os

from backend.database import init_db
from backend.auth import auth_bp
from backend.analysis import analysis_bp
from backend.dashboard import dashboard_bp

load_dotenv()

app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 10485760))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')

CORS(app, supports_credentials=True)

# Init DB
init_db()

# Blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

# ---------- FRONTEND ROUTES ----------
@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/profile')
def profile_page():
    return send_from_directory('frontend', 'profile.html')

# ---------- CATCH-ALL (KEEP LAST) ----------
@app.route('/<path:path>')
def serve_frontend(path):
    return send_from_directory('frontend', path)

# ---------- ERRORS ----------
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# ---------- RUN ----------
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)

# backend/auth.py
from flask import Blueprint, request, jsonify
from backend.auth_utils import token_required
from backend.database import users_collection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/profile", methods=["GET"])
@token_required
def get_profile(current_user):
    return jsonify({
        "username": current_user["username"],
        "email": current_user["email"]
    }), 200


@auth_bp.route("/profile", methods=["PUT"])
@token_required
def update_profile(current_user):
    data = request.get_json()

    updated_fields = {}
    if "username" in data:
        updated_fields["username"] = data["username"]
    if "email" in data:
        updated_fields["email"] = data["email"]

    users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": updated_fields}
    )

    return jsonify({"message": "Profile updated"}), 200
