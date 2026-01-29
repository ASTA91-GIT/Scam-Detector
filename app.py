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
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 10485760))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')

CORS(app, supports_credentials=True)

init_db()

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/profile')
def profile_page():
    return send_from_directory('frontend', 'profile.html')

@app.route('/<path:path>')
def serve_frontend(path):
    if path.startswith("api/"):
        return jsonify({'error': 'API route not found'}), 404
    return send_from_directory('frontend', path)

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large (max 10MB).'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)