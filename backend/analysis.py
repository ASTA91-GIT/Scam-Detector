"""
Analysis Blueprint
Handles job offer analysis, document extraction, local LLM scam analysis,
results retrieval, shareable report generation, and AI system health checks.
"""
import os
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson import ObjectId

from backend.auth_utils import require_auth
from backend.database import get_analyses_collection, get_files_collection
from backend.file_utils import save_uploaded_file, extract_text_from_file, allowed_file
from backend.ai_analyzer import run_semantic_scam_analysis
from backend.ai.provider_factory import get_ai_status
from backend.activity_utils import log_activity, create_notification
from backend.forensic_utils import (
    extract_entities,
    extract_domain_intelligence,
    build_forensic_signals,
    build_ai_opinion,
    build_document_intelligence
)
from backend.rate_limiter import apply_rate_limit
from backend.audit_logger import log_audit_event
from backend.analysis_job_manager import (
    create_analysis_job,
    get_job_status,
    start_analysis_job_async,
    _dispatch_analysis_notifications
)

analysis_bp = Blueprint('analysis', __name__)

def _calculate_pillar_scores(reasoning: list, default_val: int = 95) -> dict:
    """
    Derives 6 risk breakdown pillars from LLM forensic reasoning findings.
    Scores are 0-100 where higher is safer (0 = high risk, 100 = safe).
    """
    pillars = {
        "payment_risk": 100,
        "identity_risk": 100,
        "urgency_risk": 100,
        "contact_risk": 100,
        "company_risk": 100,
        "language_risk": 100
    }

    for item in reasoning:
        finding = (item.get("finding", "") + " " + item.get("explanation", "")).lower()
        impact = int(item.get("impact_on_score", 15))
        penalty = min(70, impact * 2)

        if any(w in finding for w in ["payment", "fee", "deposit", "money", "crypto", "usdt", "cost", "charge", "cheque", "check"]):
            pillars["payment_risk"] = max(10, pillars["payment_risk"] - penalty)
        if any(w in finding for w in ["identity", "ssn", "passport", "bank account", "sensitive", "credential", "card", "data"]):
            pillars["identity_risk"] = max(10, pillars["identity_risk"] - penalty)
        if any(w in finding for w in ["urgency", "urgent", "pressure", "immediately", "today", "expire", "24 hours", "deadline"]):
            pillars["urgency_risk"] = max(10, pillars["urgency_risk"] - penalty)
        if any(w in finding for w in ["email", "domain", "contact", "gmail", "yahoo", "telegram", "whatsapp"]):
            pillars["contact_risk"] = max(10, pillars["contact_risk"] - penalty)
        if any(w in finding for w in ["company", "impersonat", "unregistered", "fake", "website", "existence"]):
            pillars["company_risk"] = max(10, pillars["company_risk"] - penalty)
        if any(w in finding for w in ["grammar", "spelling", "manipulat", "promise", "unrealistic", "task"]):
            pillars["language_risk"] = max(10, pillars["language_risk"] - penalty)

    return pillars


@analysis_bp.route('/analyze', methods=['POST'])
@require_auth
def analyze():
    """
    Primary Scam Analysis Pipeline:
    USER UPLOAD
        ↓
    FILE VALIDATION (MIME, type, size, traversal)
        ↓
    OCR / PDF TEXT EXTRACTION
        ↓
    TEXT CLEANING & QUALITY CHECK
        ↓
    LOCAL OFFLINE LLM (Ollama)
        ↓
    SEMANTIC / CONTEXTUAL SCAM ANALYSIS
        ↓
    RISK SCORE + CONFIDENCE (0-100 clamped)
        ↓
    EVIDENCE-LINKED REASONING
        ↓
    PERSISTENCE & RETURN
    """
    user_id = request.user_id
    limit_ok, limit_msg = apply_rate_limit(f"analyze:{user_id}", limit=20, window_seconds=300)
    if not limit_ok:
        return jsonify({'error': limit_msg}), 429

    try:
        text = ""
        company_name = ""
        job_title = ""
        company_email = ""
        company_website = ""
        company_phone = ""
        job_location = ""
        file_info = None
        extraction_meta = {}

        # 1. Parse multi-part form inputs
        if request.form:
            text = (request.form.get('text') or '').strip()
            company_name = (request.form.get('company_name') or '').strip()
            job_title = (request.form.get('job_title') or '').strip()
            company_email = (request.form.get('company_email') or '').strip()
            company_website = (request.form.get('company_website') or '').strip()
            company_phone = (request.form.get('company_phone') or '').strip()
            job_location = (request.form.get('job_location') or '').strip()

        # 2. Handle file upload if present
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                file_path, filename = save_uploaded_file(file, user_id)
                file_extension = filename.rsplit('.', 1)[1].lower()

                extracted_data = extract_text_from_file(file_path, file_extension)
                extracted_text = extracted_data.get("text", "")
                if extracted_text and len(extracted_text.strip()) > 0:
                    text = extracted_text
                extraction_meta = extracted_data

                files_collection = get_files_collection()
                file_info = {
                    'user_id': user_id,
                    'filename': filename,
                    'file_path': file_path,
                    'file_type': file_extension,
                    'extraction_method': extracted_data.get("method"),
                    'is_poor_quality': extracted_data.get("is_poor", False),
                    'quality_warning': extracted_data.get("quality_warning"),
                    'uploaded_at': datetime.utcnow()
                }
                files_collection.insert_one(file_info)

        # 3. Handle JSON input if text still empty
        if not text and request.is_json:
            data = request.get_json() or {}
            text = (data.get('text') or '').strip()
            company_name = (data.get('company_name') or '').strip()
            job_title = (data.get('job_title') or '').strip()
            company_email = (data.get('company_email') or '').strip()
            company_website = (data.get('company_website') or '').strip()
            company_phone = (data.get('company_phone') or '').strip()
            job_location = (data.get('job_location') or '').strip()

        if not text or len(text.strip()) < 10:
            if file_info:
                text = text if (text and text.strip()) else "[Incomplete or unclear text extracted from uploaded document]"
                if not extraction_meta.get("quality_warning"):
                    extraction_meta["quality_warning"] = "Analysis confidence may be reduced because the extracted document text is incomplete or unclear."
                    extraction_meta["is_poor"] = True
            else:
                return jsonify({'error': 'Job description text or valid document with at least 10 characters is required.'}), 400

        # Build candidate metadata bundle
        metadata = {
            "company_name": company_name,
            "job_title": job_title,
            "company_email": company_email,
            "company_website": company_website,
            "company_phone": company_phone,
            "job_location": job_location,
            "quality_warning": extraction_meta.get("quality_warning")
        }

        # 4. PRIMARY INTELLIGENCE ENGINE: LOCAL OFFLINE LLM
        try:
            ai_result = run_semantic_scam_analysis(text=text, metadata=metadata)
        except Exception as ai_err:
            print(f"[ERROR] Local AI Analysis Error: {ai_err}")
            # Technical error reporting without silent fake fallback
            return jsonify({
                'error': f"Local AI model unavailable. Start Ollama and ensure the configured model is installed. ({str(ai_err)})"
            }), 503

        # 5. Extract calibrated metrics
        document_type = ai_result.get("document_type", "UNKNOWN")
        document_type_confidence = ai_result.get("document_type_confidence", 80)
        risk_score = ai_result["risk_score"]
        confidence = ai_result["confidence"]
        classification = ai_result["classification"]
        summary = ai_result["summary"]
        reasoning = ai_result["reasoning"]
        positive_signals = ai_result["positive_signals"]
        uncertainties = ai_result["uncertainties"]
        document_assessment = ai_result["document_assessment"]
        recommendations = ai_result["recommendations"]
        model_name = ai_result.get("model_name", "llama3.2:3b")

        # Map to display risk levels
        if classification == "HIGH_RISK":
            risk_level = "High Risk"
            risk_color = "danger"
            notif_type = "danger"
        elif classification == "MEDIUM_RISK":
            risk_level = "Suspicious"
            risk_color = "warning"
            notif_type = "warning"
        else:
            risk_level = "Safe"
            risk_color = "safe"
            notif_type = "success"

        # Trust score is the inverse of risk score (for backward compatibility)
        trust_score = max(0, min(100, 100 - risk_score))

        # Backward compatible structured red flags & risk breakdown
        structured_red_flags = []
        legacy_red_flags = []
        for r in reasoning:
            title = r.get("finding", "Risk Indicator")
            legacy_red_flags.append(title)
            structured_red_flags.append({
                "title": title,
                "severity": r.get("severity", "HIGH"),
                "explanation": r.get("explanation", ""),
                "evidence": r.get("evidence", ""),
                "recommendation": f"Independently verify this observation (Score Impact: +{r.get('impact_on_score', 0)})",
                "impact_on_score": r.get("impact_on_score", 0)
            })

        risk_breakdown = _calculate_pillar_scores(reasoning)

        # Build comprehensive forensic intelligence assets
        entities = extract_entities(text, metadata)
        domain_intelligence = extract_domain_intelligence(metadata, entities, text)
        risk_signals = build_forensic_signals(reasoning, document_type)
        ai_opinion = build_ai_opinion(ai_result, text, metadata, entities, domain_intelligence)
        document_intelligence = build_document_intelligence(ai_result, text, file_info)

        # 6. Assemble complete forensic dossier
        analysis_result = {
            "document_type": document_type,
            "document_type_confidence": document_type_confidence,
            "risk_score": risk_score,
            "trust_score": trust_score,
            "confidence": confidence,
            "classification": classification,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "summary": summary,
            "ai_explanation": summary,  # compatibility mapping
            "reasoning": reasoning,
            "positive_signals": positive_signals,
            "uncertainties": uncertainties,
            "document_assessment": document_assessment,
            "recommendations": recommendations,
            "structured_red_flags": structured_red_flags,
            "red_flags": legacy_red_flags,
            "risk_breakdown": risk_breakdown,
            "risk_signals": risk_signals,
            "entities": entities,
            "domain_intelligence": domain_intelligence,
            "ai_opinion": ai_opinion,
            "document_intelligence": document_intelligence,
            "company_name": company_name or entities.get("company", "Not Specified"),
            "job_title": job_title or entities.get("role", "Job Offer"),
            "company_email": company_email or entities.get("email", ""),
            "company_website": company_website or domain_intelligence.get("company_website", ""),
            "company_phone": company_phone or entities.get("phone", ""),
            "job_location": job_location or entities.get("location", ""),
            "model_name": model_name,
            "extraction_warning": extraction_meta.get("quality_warning"),
            "is_poor_extraction": extraction_meta.get("is_poor", False)
        }

        # 7. Persist complete record in MongoDB
        analyses_collection = get_analyses_collection()
        now = datetime.utcnow()
        record = {
            'user_id': user_id,
            'text': text[:5000],  # generous full preview
            'extracted_text': text,
            'document_type': document_type,
            'document_type_confidence': document_type_confidence,
            'company_name': analysis_result["company_name"],
            'job_title': analysis_result["job_title"],
            'company_email': company_email,
            'company_website': company_website,
            'company_phone': company_phone,
            'job_location': job_location,
            'risk_score': risk_score,
            'confidence': confidence,
            'classification': classification,
            'risk_level': risk_level,
            'trust_score': trust_score,
            'risk_color': risk_color,
            'summary': summary,
            'ai_explanation': summary,
            'reasoning': reasoning,
            'positive_signals': positive_signals,
            'uncertainties': uncertainties,
            'document_assessment': document_assessment,
            'recommendations': recommendations,
            'structured_red_flags': structured_red_flags,
            'red_flags': legacy_red_flags,
            'risk_breakdown': risk_breakdown,
            'risk_signals': risk_signals,
            'entities': entities,
            'domain_intelligence': domain_intelligence,
            'ai_opinion': ai_opinion,
            'document_intelligence': document_intelligence,
            'model_name': model_name,
            'analysis_timestamp': now,
            'file_info': file_info,
            'extraction_warning': extraction_meta.get("quality_warning"),
            'created_at': now
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
            details=f"Analyzed {analysis_result['job_title']} at {analysis_result['company_name']} (Risk: {risk_score}/100, Class: {classification})"
        )

        create_notification(
            user_id=user_id,
            title=f"Analysis Complete: {risk_level} ({risk_score}/100)",
            message=f"{analysis_result['job_title']} at {analysis_result['company_name']} analyzed via local AI.",
            notif_type=notif_type,
            link=f"result.html?id={analysis_id}"
        )

        log_audit_event("AI_ANALYSIS_COMPLETED", user_id, {
            "analysis_id": analysis_id,
            "risk_score": risk_score,
            "classification": classification,
            "document_type": document_type
        })

        # Phase 6 & 7: Check preferences and dispatch email
        _dispatch_analysis_notifications(user_id, analysis_id, analysis_result)

        return jsonify({'result': analysis_result}), 200

    except Exception as e:
        print(f"[ERROR] Analysis pipeline error: {e}")
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/job', methods=['POST'])
@require_auth
def create_job():
    """
    Phase 18: Analysis Job System.
    Submits an analysis job asynchronously and returns job_id immediately with status QUEUED.
    """
    user_id = request.user_id
    limit_ok, limit_msg = apply_rate_limit(f"job:{user_id}", limit=20, window_seconds=300)
    if not limit_ok:
        return jsonify({'error': limit_msg}), 429

    try:
        text = ""
        company_name = ""
        job_title = ""
        company_email = ""
        company_website = ""
        company_phone = ""
        job_location = ""
        file_path = None
        file_extension = None
        file_info = None

        if request.form:
            text = (request.form.get('text') or '').strip()
            company_name = (request.form.get('company_name') or '').strip()
            job_title = (request.form.get('job_title') or '').strip()
            company_email = (request.form.get('company_email') or '').strip()
            company_website = (request.form.get('company_website') or '').strip()
            company_phone = (request.form.get('company_phone') or '').strip()
            job_location = (request.form.get('job_location') or '').strip()

        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                file_path, filename = save_uploaded_file(file, user_id)
                file_extension = filename.rsplit('.', 1)[1].lower()
                file_info = {
                    'user_id': user_id,
                    'filename': filename,
                    'file_path': file_path,
                    'file_type': file_extension,
                    'uploaded_at': datetime.utcnow()
                }

        if not text and request.is_json:
            data = request.get_json() or {}
            text = (data.get('text') or '').strip()
            company_name = (data.get('company_name') or '').strip()
            job_title = (data.get('job_title') or '').strip()
            company_email = (data.get('company_email') or '').strip()
            company_website = (data.get('company_website') or '').strip()
            company_phone = (data.get('company_phone') or '').strip()
            job_location = (data.get('job_location') or '').strip()

        if not text and not file_path:
            return jsonify({'error': 'Job description text or valid document upload is required.'}), 400

        payload = {
            "text": text,
            "metadata": {
                "company_name": company_name,
                "job_title": job_title,
                "company_email": company_email,
                "company_website": company_website,
                "company_phone": company_phone,
                "job_location": job_location
            },
            "file_path": file_path,
            "file_extension": file_extension,
            "file_info": file_info
        }

        job_id = create_analysis_job(user_id=user_id, input_payload=payload)
        start_analysis_job_async(job_id)

        return jsonify({
            "job_id": job_id,
            "status": "QUEUED",
            "progress": 5,
            "stage": "UPLOAD"
        }), 202

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/job/<job_id>', methods=['GET'])
@require_auth
def get_job(job_id):
    """
    Phase 19: Real-time Analysis Status.
    Pollable status endpoint reporting actual backend stages:
    VALIDATION -> OCR -> ENTITY_EXTRACTION -> DOMAIN_INTELLIGENCE -> AI_ANALYSIS -> REPORT_GENERATION -> COMPLETED
    """
    job_info = get_job_status(job_id)
    if not job_info:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify({"job": job_info}), 200


def _sanitize_doc_for_json(d):
    """Recursively convert ObjectIds and datetimes to JSON-serializable types"""
    if isinstance(d, dict):
        return {k: _sanitize_doc_for_json(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [_sanitize_doc_for_json(x) for x in d]
    elif isinstance(d, ObjectId):
        return str(d)
    elif isinstance(d, datetime):
        return d.isoformat()
    return d


@analysis_bp.route('/result/<analysis_id>', methods=['GET'])
@analysis_bp.route('/<analysis_id>', methods=['GET'])
@require_auth
def get_analysis_result(analysis_id):
    """Retrieve full analysis result for a given ID with per-user authorization"""
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
        if 'analysis_timestamp' in doc and hasattr(doc['analysis_timestamp'], 'isoformat'):
            doc['analysis_timestamp'] = doc['analysis_timestamp'].isoformat()

        # On-the-fly enrichment if record is missing modern forensic fields
        if 'ai_opinion' not in doc:
            doc_text = doc.get('extracted_text') or doc.get('text') or ''
            doc_meta = {
                'company_name': doc.get('company_name'),
                'job_title': doc.get('job_title'),
                'company_email': doc.get('company_email'),
                'company_website': doc.get('company_website'),
                'company_phone': doc.get('company_phone'),
                'job_location': doc.get('job_location')
            }
            ents = extract_entities(doc_text, doc_meta)
            dom_intel = extract_domain_intelligence(doc_meta, ents, doc_text)
            r_signals = build_forensic_signals(doc.get('reasoning', []), doc.get('document_type', 'JOB_OFFER'))
            ai_op = build_ai_opinion(doc, doc_text, doc_meta, ents, dom_intel)
            d_intel = build_document_intelligence(doc, doc_text, doc.get('file_info'))

            doc['entities'] = ents
            doc['domain_intelligence'] = dom_intel
            doc['risk_signals'] = r_signals
            doc['ai_opinion'] = ai_op
            doc['document_intelligence'] = d_intel

        clean_doc = _sanitize_doc_for_json(doc)
        return jsonify({'analysis': clean_doc}), 200

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

        # On-the-fly enrichment if missing forensic fields
        if 'ai_opinion' not in doc:
            doc_text = doc.get('extracted_text') or doc.get('text') or ''
            doc_meta = {
                'company_name': doc.get('company_name'),
                'job_title': doc.get('job_title'),
                'company_email': doc.get('company_email'),
                'company_website': doc.get('company_website'),
                'company_phone': doc.get('company_phone'),
                'job_location': doc.get('job_location')
            }
            ents = extract_entities(doc_text, doc_meta)
            dom_intel = extract_domain_intelligence(doc_meta, ents, doc_text)
            r_signals = build_forensic_signals(doc.get('reasoning', []), doc.get('document_type', 'JOB_OFFER'))
            ai_op = build_ai_opinion(doc, doc_text, doc_meta, ents, dom_intel)
            d_intel = build_document_intelligence(doc, doc_text, doc.get('file_info'))

            doc['entities'] = ents
            doc['domain_intelligence'] = dom_intel
            doc['risk_signals'] = r_signals
            doc['ai_opinion'] = ai_op
            doc['document_intelligence'] = d_intel

        # Sanitize sensitive account details
        sanitized = {
            'analysis_id': str(doc['_id']),
            'document_type': doc.get('document_type', 'UNKNOWN'),
            'document_type_confidence': doc.get('document_type_confidence', 80),
            'company_name': doc.get('company_name', 'Company Offer'),
            'job_title': doc.get('job_title', 'Job Offer'),
            'company_website': doc.get('company_website', ''),
            'risk_score': doc.get('risk_score', 100 - doc.get('trust_score', 50)),
            'confidence': doc.get('confidence', 85),
            'classification': doc.get('classification', 'MEDIUM_RISK'),
            'risk_level': doc.get('risk_level', 'Unknown'),
            'trust_score': doc.get('trust_score', 0),
            'risk_color': doc.get('risk_color', 'warning'),
            'summary': doc.get('summary', doc.get('ai_explanation', '')),
            'ai_explanation': doc.get('ai_explanation', doc.get('summary', '')),
            'reasoning': doc.get('reasoning', []),
            'positive_signals': doc.get('positive_signals', []),
            'uncertainties': doc.get('uncertainties', []),
            'document_assessment': doc.get('document_assessment', {}),
            'recommendations': doc.get('recommendations', []),
            'structured_red_flags': doc.get('structured_red_flags', []),
            'red_flags': doc.get('red_flags', []),
            'risk_breakdown': doc.get('risk_breakdown', {}),
            'risk_signals': doc.get('risk_signals', []),
            'entities': doc.get('entities', {}),
            'domain_intelligence': doc.get('domain_intelligence', {}),
            'ai_opinion': doc.get('ai_opinion', {}),
            'document_intelligence': doc.get('document_intelligence', {}),
            'model_name': doc.get('model_name', 'llama3.2:3b'),
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


@analysis_bp.route('/ai/status', methods=['GET'])
def ai_status():
    """Diagnostics endpoint for local AI and Ollama readiness"""
    status = get_ai_status()
    return jsonify(status), 200


# ==============================================================================
# SECTION 31: ANALYSIS COMPARISON
# ==============================================================================
def _find_analysis_doc(col, doc_id):
    """Safely retrieves analysis document whether stored by ObjectId or string UUID."""
    if not doc_id:
        return None
    try:
        if ObjectId.is_valid(str(doc_id)):
            doc = col.find_one({'_id': ObjectId(str(doc_id))})
            if doc:
                return doc
    except Exception:
        pass
    return col.find_one({'_id': str(doc_id)})


def _extract_finding_str(item):
    """Safely extracts text representation of a finding or red flag."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get('title') or item.get('finding') or item.get('indicator') or str(item)
    return str(item)


@analysis_bp.route('/compare', methods=['GET'])
@require_auth
def compare_analyses():
    """
    Compares two forensic analyses side-by-side.
    Returns delta in risk score, classification shift, entity changes,
    added/removed findings, and critical signal shifts.
    """
    try:
        id1 = request.args.get('id1', '').strip()
        id2 = request.args.get('id2', '').strip()

        if not id1 or not id2:
            return jsonify({'error': {'code': 'MISSING_PARAMS', 'message': 'Both id1 and id2 parameters are required.'}}), 400

        user_id = request.user_id
        col = get_analyses_collection()

        doc1 = _find_analysis_doc(col, id1)
        doc2 = _find_analysis_doc(col, id2)

        if not doc1 or not doc2:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'One or both analyses could not be found.'}}), 404

        role = getattr(request, 'user_role', 'USER')
        if role != 'ADMIN':
            if str(doc1.get('user_id')) != user_id or str(doc2.get('user_id')) != user_id:
                return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'You are not authorized to compare these analyses.'}}), 403

        score1 = int(doc1.get('risk_score', 0))
        score2 = int(doc2.get('risk_score', 0))
        score_diff = score2 - score1

        class1 = doc1.get('risk_level', doc1.get('classification', 'LOW_RISK'))
        class2 = doc2.get('risk_level', doc2.get('classification', 'LOW_RISK'))

        entities1 = doc1.get('entities') or doc1.get('extracted_entities') or {}
        entities2 = doc2.get('entities') or doc2.get('extracted_entities') or {}

        entity_diffs = []
        changed_entities = {}
        for key in ['company_name', 'company', 'job_title', 'role', 'salary', 'recruiter_email', 'company_website', 'payment', 'phone', 'location']:
            val1 = entities1.get(key) or doc1.get(key)
            val2 = entities2.get(key) or doc2.get(key)
            if val1 or val2:
                v1_str = str(val1) if val1 else 'Not Specified'
                v2_str = str(val2) if val2 else 'Not Specified'
                if v1_str != v2_str:
                    clean_field = key.replace('_', ' ').title()
                    entity_diffs.append({
                        'field': clean_field,
                        'from': v1_str,
                        'to': v2_str
                    })
                    changed_entities[key] = {'doc1': v1_str, 'doc2': v2_str}

        raw_f1 = (doc1.get('structured_red_flags') or []) + (doc1.get('findings') or []) + (doc1.get('red_flags') or [])
        raw_f2 = (doc2.get('structured_red_flags') or []) + (doc2.get('findings') or []) + (doc2.get('red_flags') or [])

        findings1 = {_extract_finding_str(f) for f in raw_f1 if f}
        findings2 = {_extract_finding_str(f) for f in raw_f2 if f}

        added_findings = list(findings2 - findings1)
        removed_findings = list(findings1 - findings2)

        return jsonify({
            'id1': id1,
            'id2': id2,
            'doc1_title': doc1.get('filename') or doc1.get('job_title') or doc1.get('company_name') or 'Document 1',
            'doc2_title': doc2.get('filename') or doc2.get('job_title') or doc2.get('company_name') or 'Document 2',
            'score1': score1,
            'score2': score2,
            'score_diff': score_diff,
            'classification1': class1,
            'classification2': class2,
            'classification_changed': class1 != class2,
            'changed_entities': changed_entities,
            'entity_diffs': entity_diffs,
            'added_findings': added_findings,
            'removed_findings': removed_findings,
            'comparison': {
                'analysis_1': {
                    'id': id1,
                    'title': doc1.get('job_title') or doc1.get('company_name') or 'Document 1',
                    'risk_score': score1,
                    'classification': class1,
                    'created_at': doc1.get('created_at').isoformat() if hasattr(doc1.get('created_at'), 'isoformat') else str(doc1.get('created_at'))
                },
                'analysis_2': {
                    'id': id2,
                    'title': doc2.get('job_title') or doc2.get('company_name') or 'Document 2',
                    'risk_score': score2,
                    'classification': class2,
                    'created_at': doc2.get('created_at').isoformat() if hasattr(doc2.get('created_at'), 'isoformat') else str(doc2.get('created_at'))
                },
                'risk_score_delta': score_diff,
                'classification_shifted': class1 != class2,
                'entity_diffs': entity_diffs,
                'added_findings': added_findings,
                'removed_findings': removed_findings
            }
        }), 200

    except Exception as e:
        return jsonify({'error': {'code': 'COMPARE_ERROR', 'message': str(e)}}), 500


# ==============================================================================
# SECTION 36: WHAT-IF RISK SIMULATION
# ==============================================================================
@analysis_bp.route('/<analysis_id>/simulate', methods=['POST'])
@require_auth
def simulate_risk(analysis_id):
    """
    Performs 'What-If' forensic risk modeling on a case.
    Computes simulated risk score without altering the stored analysis record.
    """
    try:
        col = get_analyses_collection()
        doc = _find_analysis_doc(col, analysis_id)
        if not doc:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Analysis not found.'}}), 404

        role = getattr(request, 'user_role', 'USER')
        if role != 'ADMIN' and str(doc.get('user_id')) != request.user_id:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Unauthorized.'}}), 403

        data = request.get_json() or {}
        base_score = int(doc.get('risk_score', 0))
        simulated_score = base_score
        active_factors = []

        # Handle list format: 'scenarios': [{'type': 'advance_fee', ...}, ...]
        scenarios = data.get('scenarios', [])
        for sc in scenarios:
            stype = sc.get('type')
            if stype in ['advance_fee', 'fee', 'payment']:
                fee_val = sc.get('fee_amount', '₹5,000')
                simulated_score += 45
                active_factors.append(f"Hypothetical Upfront Advance Fee Demanded ({fee_val})")
            elif stype in ['crypto', 'crypto_payment']:
                simulated_score += 30
                active_factors.append("Hypothetical Payment Solicited via Cryptocurrency / Telegram")
            elif stype in ['urgency']:
                simulated_score += 15
                active_factors.append("Hypothetical Artificial Urgency (< 24hr Deadline to sign/pay)")
            elif stype in ['domain_mismatch']:
                simulated_score += 25
                active_factors.append("Hypothetical Free Public Recruiter Email (@gmail.com)")
            elif stype in ['sensitive_docs']:
                simulated_score += 20
                active_factors.append("Hypothetical Premature Sensitive Credential / Bank Account Demand")

        # Handle direct boolean flags
        if data.get('add_fee_request'):
            fee_val = data.get('fee_amount', '₹5,000')
            simulated_score += 45
            active_factors.append(f"Hypothetical Upfront Advance Fee Demanded ({fee_val})")

        if data.get('add_crypto_payment'):
            simulated_score += 30
            active_factors.append("Hypothetical Payment Solicited via Cryptocurrency / Telegram")

        if data.get('add_urgency'):
            simulated_score += 15
            active_factors.append("Hypothetical Artificial Urgency (< 24hr Deadline to sign/pay)")

        if data.get('add_domain_mismatch'):
            simulated_score += 25
            active_factors.append("Hypothetical Free Public Recruiter Email (@gmail.com)")

        if data.get('add_sensitive_docs'):
            simulated_score += 20
            active_factors.append("Hypothetical Premature Sensitive Credential / Bank Account Demand")

        if data.get('remove_fee_request') and base_score > 30:
            simulated_score -= 40
            active_factors.append("Hypothetical Verified Zero-Fee Corporate Policy")

        simulated_score = max(0, min(100, simulated_score))

        if simulated_score >= 70:
            sim_class = "HIGH RISK"
        elif simulated_score >= 40:
            sim_class = "MEDIUM RISK"
        else:
            sim_class = "LOW RISK"

        return jsonify({
            'simulation': True,
            'simulated_score': simulated_score,
            'hypothetical_findings': active_factors,
            'original_score': base_score,
            'simulated_classification': sim_class,
            'simulation_details': {
                'case_id': str(analysis_id),
                'is_simulation': True,
                'disclaimer': 'SIMULATION ONLY: Hypothetical risk modeling for investigative analysis. Original case remains untouched.',
                'original_risk_score': base_score,
                'simulated_risk_score': simulated_score,
                'delta': simulated_score - base_score,
                'original_classification': doc.get('risk_level', 'LOW_RISK'),
                'simulated_classification': sim_class,
                'triggered_factors': active_factors
            }
        }), 200

    except Exception as e:
        return jsonify({'error': {'code': 'SIMULATION_ERROR', 'message': str(e)}}), 500


# ==============================================================================
# SECTION 34: RECOMMENDED ACTIONS CHECKLIST PERSISTENCE
# ==============================================================================
@analysis_bp.route('/<analysis_id>/checklist', methods=['GET', 'PATCH'])
@require_auth
def manage_checklist(analysis_id):
    """
    Persists and retrieves user's completed verification checklist items for an analysis.
    """
    try:
        col = get_analyses_collection()
        doc = _find_analysis_doc(col, analysis_id)
        if not doc:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Analysis not found.'}}), 404

        role = getattr(request, 'user_role', 'USER')
        if role != 'ADMIN' and str(doc.get('user_id')) != request.user_id:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Unauthorized.'}}), 403

        saved_state = doc.get('checklist_state', {
            'checked_indices': [],
            'completed_count': 0,
            'total_items': 0
        })

        rec_actions = doc.get('recommended_actions') or [
            'Verify company registration through official corporate registry',
            'Confirm offer with company HR using official domain email',
            'Do not pay any upfront processing or equipment deposit fees',
            'Do not share PAN, Aadhaar, or bank details before formal onboarding',
            'Check company website domain registration age and authenticity'
        ]

        if request.method == 'GET':
            saved_indices = set(saved_state.get('checked_indices', []))
            checklist_items = []
            for idx, act in enumerate(rec_actions):
                checklist_items.append({
                    'index': idx,
                    'action': act,
                    'completed': idx in saved_indices
                })

            return jsonify({
                'case_id': str(analysis_id),
                'checklist': checklist_items,
                'completed_count': len(saved_indices),
                'total_items': len(rec_actions),
                'checklist_state': saved_state
            }), 200

        # PATCH
        data = request.get_json() or {}
        checked_indices = list(saved_state.get('checked_indices', []))

        # Check if single item toggled: {'index': 0, 'completed': True}
        if 'index' in data:
            item_idx = int(data['index'])
            is_completed = bool(data.get('completed', True))
            if is_completed:
                if item_idx not in checked_indices:
                    checked_indices.append(item_idx)
            else:
                if item_idx in checked_indices:
                    checked_indices.remove(item_idx)
        elif 'checked_indices' in data:
            checked_indices = [int(i) for i in data['checked_indices']]

        total_items = data.get('total_items', len(rec_actions))
        state = {
            'checked_indices': checked_indices,
            'completed_count': len(checked_indices),
            'total_items': total_items,
            'updated_at': datetime.utcnow().isoformat()
        }

        # Update in database
        doc_filter = {'_id': ObjectId(str(analysis_id))} if ObjectId.is_valid(str(analysis_id)) else {'_id': str(analysis_id)}
        col.update_one(doc_filter, {'$set': {'checklist_state': state}})

        saved_indices = set(checked_indices)
        checklist_items = []
        for idx, act in enumerate(rec_actions):
            checklist_items.append({
                'index': idx,
                'action': act,
                'completed': idx in saved_indices
            })

        return jsonify({
            'message': 'Checklist progress saved.',
            'checklist': checklist_items,
            'completed_count': len(checked_indices),
            'total_items': total_items,
            'checklist_state': state
        }), 200

    except Exception as e:
        return jsonify({'error': {'code': 'CHECKLIST_ERROR', 'message': str(e)}}), 500

