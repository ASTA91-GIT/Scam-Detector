"""
Main Flask Application
AI-Powered Job & Internship Scam Detector
"""
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os

from backend.database import init_db
from backend.auth import auth_bp
from backend.analysis import analysis_bp
from backend.dashboard import dashboard_bp

load_dotenv()

app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = 'uploads'

CORS(app, supports_credentials=True)

# Initialize Database
init_db()

# 1. Register Blueprints (Order matters: API first)
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

# 2. Specific Frontend Routes
@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/profile')
def profile_page():
    return send_from_directory('frontend', 'profile.html')

# 3. Catch-all Route (Keep this LAST)
@app.route('/<path:path>')
def serve_frontend(path):
    # If the file exists in frontend folder, serve it
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory('frontend', path)
    # Otherwise, default to index (for SPA-like behavior)
    return send_from_directory('frontend', 'index.html')

# Error Handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)