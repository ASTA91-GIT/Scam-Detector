"""
Analysis Blueprint
Handles job offer analysis, document extraction, results retrieval,
URL security scanning, and shareable report generation.
"""
from flask import Blueprint, request, jsonify
from backend.auth_utils import require_auth
from backend.database import get_analyses_collection, get_files_collection
from backend.file_utils import save_uploaded_file, extract_text_from_file, allowed_file
from backend.scam_detector import analyze_job_offer, scan_url_safety
from backend.ai_analyzer import ai_scam_analysis
from backend.activity_utils import log_activity, create_notification
from datetime import datetime
from bson import ObjectId

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analyze', methods=['POST'])
@require_auth
def analyze():
    try:
        user_id = request.user_id
        text = None
        company_name = ""
        job_title = ""
        company_email = None
        company_website = None
        company_phone = None
        job_location = None
        file_info = None

        # Check for multi-part form data
        if request.form:
            text = request.form.get('text', '').strip()
            company_name = request.form.get('company_name', '').strip()
            job_title = request.form.get('job_title', '').strip()
            company_email = request.form.get('company_email', '').strip()
            company_website = request.form.get('company_website', '').strip()
            company_phone = request.form.get('company_phone', '').strip()
            job_location = request.form.get('job_location', '').strip()

        # Handle file upload if present
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                file_path, filename = save_uploaded_file(file, user_id)
                file_extension = filename.rsplit('.', 1)[1].lower()
                extracted = extract_text_from_file(file_path, file_extension)
                if extracted and len(extracted.strip()) > 0:
                    text = extracted

                files_collection = get_files_collection()
                file_info = {
                    'user_id': user_id,
                    'filename': filename,
                    'file_path': file_path,
                    'file_type': file_extension,
                    'uploaded_at': datetime.utcnow()
                }
                files_collection.insert_one(file_info)

        # Handle JSON input if text still empty
        if not text and request.is_json:
            data = request.get_json() or {}
            text = data.get('text', '').strip()
            company_name = data.get('company_name', '').strip()
            job_title = data.get('job_title', '').strip()
            company_email = data.get('company_email', '').strip()
            company_website = data.get('company_website', '').strip()
            company_phone = data.get('company_phone', '').strip()
            job_location = data.get('job_location', '').strip()

        if not text or len(text.strip()) < 10:
            return jsonify({'error': 'Job description text or valid document with at least 10 characters is required.'}), 400

        # ---------- FORENSIC RULE ANALYSIS ----------
        analysis_result = analyze_job_offer(
            text=text,
            company_email=company_email or None,
            company_website=company_website or None,
            company_name=company_name or None,
            job_title=job_title or None
        )

        # -----------------------------
        # AI EXPLANATION
        # -----------------------------
        try:
            ai_explanation = ai_scam_analysis(
                text=text,
                rule_result=analysis_result
            )
        except Exception as ai_error:
            print("❌ AI explanation error:", ai_error)
            ai_explanation = "AI explanation unavailable. Forensic pattern engine findings apply."

        analysis_result["ai_explanation"] = ai_explanation
        analysis_result["ai_enabled"] = True
        analysis_result["company_name"] = company_name or "Not Specified"
        analysis_result["job_title"] = job_title or "Job Offer"
        analysis_result["company_phone"] = company_phone or ""
        analysis_result["job_location"] = job_location or ""

        # ---------- SAVE COMPLETE RECORD IN MONGODB ----------
        analyses_collection = get_analyses_collection()
        record = {
            'user_id': user_id,
            'text': text[:3000],  # store generous preview
            'company_name': analysis_result["company_name"],
            'job_title': analysis_result["job_title"],
            'company_email': company_email,
            'company_website': company_website,
            'company_phone': company_phone,
            'job_location': job_location,
            'risk_level': analysis_result['risk_level'],
            'trust_score': analysis_result['trust_score'],
            'risk_color': analysis_result['risk_color'],
            'risk_breakdown': analysis_result['risk_breakdown'],
            'explanations': analysis_result['explanations'],
            'ai_explanation': ai_explanation,
            'structured_red_flags': analysis_result.get('structured_red_flags', []),
            'red_flags': analysis_result.get('red_flags', []),
            'recommendations': analysis_result.get('recommendations', []),
            'keyword_score': analysis_result.get('keyword_score', 0),
            'keyword_detections': analysis_result.get('keyword_detections', {}),
            'urgency_score': analysis_result.get('urgency_score', 0),
            'grammar_issues': analysis_result.get('grammar_issues', 0),
            'financial_flags_count': analysis_result.get('financial_flags_count', 0),
            'email_domain_suspicious': analysis_result.get('email_domain_suspicious', False),
            'website_exists': analysis_result.get('website_exists', True),
            'company_match': analysis_result.get('company_match', True),
            'file_info': file_info,
            'created_at': datetime.utcnow()
        }

        insert_res = analyses_collection.insert_one(record)
        analysis_id = str(insert_res.inserted_id)

        analysis_result['analysis_id'] = analysis_id
        analysis_result['_id'] = analysis_id
        analysis_result['created_at'] = record['created_at'].isoformat()

        # Audit log and in-app notification
        log_activity(
            user_id=user_id,
            action="analysis_completed",
            details=f"Analyzed {analysis_result['job_title']} at {analysis_result['company_name']} (Risk: {analysis_result['risk_level']}, Score: {analysis_result['trust_score']})"
        )

        notif_type = 'danger' if analysis_result['risk_level'] == 'High Risk' else ('warning' if analysis_result['risk_level'] == 'Suspicious' else 'success')
        create_notification(
            user_id=user_id,
            title=f"Analysis Complete: {analysis_result['risk_level']}",
            message=f"{analysis_result['job_title']} scored {analysis_result['trust_score']}/100 trust score.",
            notif_type=notif_type,
            link=f"result.html?id={analysis_id}"
        )

        return jsonify({'result': analysis_result}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/result/<analysis_id>', methods=['GET'])
@analysis_bp.route('/<analysis_id>', methods=['GET'])
@require_auth
def get_analysis_result(analysis_id):
    """Retrieve full analysis result for a given ID"""
    try:
        user_id = request.user_id
        analyses_collection = get_analyses_collection()

        try:
            obj_id = ObjectId(analysis_id)
        except Exception:
            return jsonify({'error': 'Invalid analysis ID'}), 400

        doc = analyses_collection.find_one({'_id': obj_id, 'user_id': user_id})
        if not doc:
            return jsonify({'error': 'Analysis not found or unauthorized access'}), 404

        doc['_id'] = str(doc['_id'])
        doc['analysis_id'] = str(doc['_id'])
        if 'created_at' in doc and hasattr(doc['created_at'], 'isoformat'):
            doc['created_at'] = doc['created_at'].isoformat()

        return jsonify({'analysis': doc}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/share/<analysis_id>', methods=['GET'])
def get_shared_analysis(analysis_id):
    """Public read-only sanitized view of an analysis report"""
    try:
        analyses_collection = get_analyses_collection()
        try:
            obj_id = ObjectId(analysis_id)
        except Exception:
            return jsonify({'error': 'Invalid analysis ID'}), 400

        doc = analyses_collection.find_one({'_id': obj_id})
        if not doc:
            return jsonify({'error': 'Shared report not found'}), 404

        # Sanitize sensitive account details
        sanitized = {
            'analysis_id': str(doc['_id']),
            'company_name': doc.get('company_name', 'Company Offer'),
            'job_title': doc.get('job_title', 'Job Offer'),
            'company_website': doc.get('company_website', ''),
            'risk_level': doc.get('risk_level', 'Unknown'),
            'trust_score': doc.get('trust_score', 0),
            'risk_color': doc.get('risk_color', 'warning'),
            'risk_breakdown': doc.get('risk_breakdown', {}),
            'explanations': doc.get('explanations', []),
            'ai_explanation': doc.get('ai_explanation', ''),
            'structured_red_flags': doc.get('structured_red_flags', []),
            'red_flags': doc.get('red_flags', []),
            'recommendations': doc.get('recommendations', []),
            'created_at': doc.get('created_at').isoformat() if hasattr(doc.get('created_at'), 'isoformat') else str(doc.get('created_at'))
        }

        return jsonify({'report': sanitized}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/scan-url', methods=['POST'])
@require_auth
def scan_url():
    """Scan and evaluate a URL for phishing and fraudulent indicators"""
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()
        company_name = data.get('company_name', '').strip()

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        scan_result = scan_url_safety(url, company_name)
        return jsonify({'scan': scan_result}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
