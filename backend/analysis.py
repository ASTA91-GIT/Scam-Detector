"""
Analysis Blueprint
Handles job offer analysis requests
"""
from flask import Blueprint, request, jsonify
from backend.auth_utils import require_auth
from backend.database import get_analyses_collection, get_files_collection
from backend.file_utils import save_uploaded_file, extract_text_from_file, allowed_file
from backend.scam_detector import analyze_job_offer
from datetime import datetime
from bson import ObjectId
from backend.ai_analyzer import ai_scam_analysis
import os

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analyze', methods=['POST'])
@require_auth
def analyze():
    """Analyze job offer text, file, or URL"""
    try:
        user_id = request.user_id
        text = None
        company_email = None
        company_website = None
        file_info = None
        
        # Check if file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename and allowed_file(file.filename):
                # Save file
                file_path, filename = save_uploaded_file(file, user_id)
                file_extension = filename.rsplit('.', 1)[1].lower()
                
                # Extract text from file
                text = extract_text_from_file(file_path, file_extension)
                
                # Store file info
                files_collection = get_files_collection()
                file_info = {
                    'user_id': user_id,
                    'filename': filename,
                    'file_path': file_path,
                    'file_type': file_extension,
                    'uploaded_at': datetime.utcnow()
                }
                files_collection.insert_one(file_info)
                file_info['_id'] = str(file_info['_id'])
        
        # Get text from form data or JSON
        if not text:
            if request.is_json:
                data = request.get_json()
                text = data.get('text', '')
                company_email = data.get('company_email', '')
                company_website = data.get('company_website', '')
            else:
                text = request.form.get('text', '')
                company_email = request.form.get('company_email', '')
                company_website = request.form.get('company_website', '')
        
        # Validate text input
        if not text or len(text.strip()) < 10:
            return jsonify({
                'error': 'Please provide job description text (minimum 10 characters) or upload a file'
            }), 400
        
        # Perform analysis
        analysis_result = analyze_job_offer(
            text=text,
            company_email=company_email if company_email else None,
            company_website=company_website if company_website else None
        )

        # -----------------------------
        # AI ANALYSIS (GOOGLE GEMINI)
        # -----------------------------
        try:
            ai_analysis = ai_scam_analysis(
                text=text,
                rule_result=analysis_result
            )
        except Exception as ai_error:
            ai_analysis = (
                "AI analysis failed. Please rely on rule-based detection."
            )

        analysis_result["ai_analysis"] = str(ai_analysis)
        analysis_result["ai_enabled"] = True
        
        # Store analysis in database
        analyses_collection = get_analyses_collection()
        analysis_record = {
            'user_id': user_id,
            'text': text[:1000],  # Store first 1000 chars
            'company_email': company_email,
            'company_website': company_website,
            'trust_score': analysis_result['trust_score'],
            'risk_level': analysis_result['risk_level'],
            'risk_color': analysis_result['risk_color'],
            'keyword_detections': analysis_result['keyword_detections'],
            'keyword_score': analysis_result['keyword_score'],
            'urgency_score': analysis_result['urgency_score'],
            'grammar_issues': analysis_result['grammar_issues'],
            'financial_flags_count': analysis_result['financial_flags_count'],
            'email_domain_suspicious': analysis_result['email_domain_suspicious'],
            'website_exists': analysis_result['website_exists'],
            'company_match': analysis_result['company_match'],
            'explanations': analysis_result['explanations'],
            'ai_explanation': analysis_result.get('ai_explanation'),
            'file_info': file_info,
            'created_at': datetime.utcnow()
        }
        
        result = analyses_collection.insert_one(analysis_record)
        analysis_id = str(result.inserted_id)
        
        # Add analysis ID to result
        analysis_result['analysis_id'] = analysis_id
        analysis_result['created_at'] = analysis_record['created_at'].isoformat()
        
        return jsonify({
            'message': 'Analysis completed',
            'result': analysis_result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@analysis_bp.route('/result/<analysis_id>', methods=['GET'])
@require_auth
def get_result(analysis_id):
    """Get analysis result by ID"""
    try:
        user_id = request.user_id
        analyses_collection = get_analyses_collection()
        
        analysis = analyses_collection.find_one({
            '_id': ObjectId(analysis_id),
            'user_id': user_id
        })
        
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Convert ObjectId to string
        analysis['_id'] = str(analysis['_id'])
        if 'file_info' in analysis and analysis['file_info'] and '_id' in analysis['file_info']:
            analysis['file_info']['_id'] = str(analysis['file_info']['_id'])
        
        # Convert datetime to ISO format
        if 'created_at' in analysis:
            analysis['created_at'] = analysis['created_at'].isoformat()
        
        return jsonify({
            'analysis': analysis
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve analysis: {str(e)}'}), 500
