from flask import Blueprint, request, jsonify
from backend.auth_utils import require_auth
from backend.database import get_analyses_collection, get_files_collection
from backend.file_utils import save_uploaded_file, extract_text_from_file, allowed_file
from backend.scam_detector import analyze_job_offer
from backend.ai_analyzer import ai_scam_analysis
from datetime import datetime
from bson import ObjectId

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analyze', methods=['POST'])
@require_auth
def analyze():
    try:
        user_id = request.user_id
        text = None
        company_email = None
        company_website = None
        file_info = None

        # ---------- FILE ----------
        if 'file' in request.files:
            file = request.files['file']
            if file.filename and allowed_file(file.filename):
                file_path, filename = save_uploaded_file(file, user_id)
                file_extension = filename.rsplit('.', 1)[1].lower()
                text = extract_text_from_file(file_path, file_extension)

                files_collection = get_files_collection()
                file_info = {
                    'user_id': user_id,
                    'filename': filename,
                    'file_path': file_path,
                    'file_type': file_extension,
                    'uploaded_at': datetime.utcnow()
                }
                files_collection.insert_one(file_info)

        # ---------- TEXT ----------
        if not text:
            data = request.get_json() if request.is_json else request.form
            text = data.get('text', '')
            company_email = data.get('company_email', '')
            company_website = data.get('company_website', '')

        if not text or len(text.strip()) < 10:
            return jsonify({'error': 'Text too short'}), 400

        # ---------- RULE ANALYSIS ----------
        analysis_result = analyze_job_offer(
            text=text,
            company_email=company_email or None,
            company_website=company_website or None
        )
     # -----------------------------
# AI ANALYSIS (GEMINI)
# -----------------------------
        try:
          ai_explanation = ai_scam_analysis(
        text=text,
        rule_result=analysis_result
         )
        except Exception as ai_error:
           print("❌ Gemini error:", ai_error)
        ai_explanation = "AI explanation unavailable. Please rely on rule-based analysis."

        analysis_result["ai_explanation"] = ai_explanation
        analysis_result["ai_enabled"] = True


        # ---------- SAVE ----------
        analyses = get_analyses_collection()
        record = {
            'user_id': user_id,
            'text': text[:1000],
            'risk_level': analysis_result['risk_level'],
            'trust_score': analysis_result['trust_score'],
            'explanations': analysis_result['explanations'],
            'ai_explanation': ai_explanation,
            'created_at': datetime.utcnow()
        }
        result = analyses.insert_one(record)

        analysis_result['analysis_id'] = str(result.inserted_id)
        analysis_result['created_at'] = record['created_at'].isoformat()

        return jsonify({'result': analysis_result}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

