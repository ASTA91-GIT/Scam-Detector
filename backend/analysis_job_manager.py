"""
Analysis Job Manager & Background Task Processor
Manages multi-stage forensic analysis jobs:
QUEUED -> VALIDATION -> OCR / TEXT_EXTRACTION -> ENTITY_EXTRACTION -> DOMAIN_INTELLIGENCE -> AI_ANALYSIS -> REPORT_GENERATION -> COMPLETED / FAILED
"""

import os
import uuid
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.database import get_database, get_analyses_collection, get_files_collection, get_users_collection
from backend.file_utils import extract_text_from_file
from backend.ai_analyzer import run_semantic_scam_analysis
from backend.activity_utils import log_activity, create_notification
from backend.forensic_utils import (
    extract_entities,
    extract_domain_intelligence,
    extract_url_intelligence,
    build_forensic_signals,
    build_ai_opinion,
    build_document_intelligence
)
from backend.audit_logger import log_audit_event
from backend.mail_client import send_email

logger = logging.getLogger("scamguard.analysis_job")

# Thread pool / active workers dict
_ACTIVE_JOBS: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def _get_jobs_collection():
    db = get_database()
    return db["analysis_jobs"]


def create_analysis_job(user_id: str, input_payload: Dict[str, Any]) -> str:
    """
    Initializes a new analysis job record with status QUEUED.
    """
    job_id = f"JOB-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.utcnow()

    job_data = {
        "job_id": job_id,
        "user_id": str(user_id),
        "status": "QUEUED",
        "progress": 5,
        "stage": "UPLOAD",
        "stage_history": [
            {"stage": "UPLOAD", "status": "COMPLETED", "timestamp": now.isoformat()}
        ],
        "input_payload": input_payload,
        "result": None,
        "analysis_id": None,
        "error": None,
        "created_at": now,
        "updated_at": now
    }

    try:
        jobs_coll = _get_jobs_collection()
        jobs_coll.insert_one(job_data)
    except Exception as e:
        logger.warning(f"Could not persist job to MongoDB: {e}")

    with _LOCK:
        _ACTIVE_JOBS[job_id] = job_data

    return job_id


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves current job status, progress, stage, and result if completed.
    """
    with _LOCK:
        if job_id in _ACTIVE_JOBS:
            job = _ACTIVE_JOBS[job_id]
            return {
                "job_id": job.get("job_id"),
                "status": job.get("status"),
                "progress": job.get("progress"),
                "stage": job.get("stage"),
                "stage_history": job.get("stage_history", []),
                "analysis_id": job.get("analysis_id"),
                "result": job.get("result"),
                "error": job.get("error")
            }

    try:
        jobs_coll = _get_jobs_collection()
        doc = jobs_coll.find_one({"job_id": job_id})
        if doc:
            return {
                "job_id": doc.get("job_id"),
                "status": doc.get("status"),
                "progress": doc.get("progress"),
                "stage": doc.get("stage"),
                "stage_history": doc.get("stage_history", []),
                "analysis_id": doc.get("analysis_id"),
                "result": doc.get("result"),
                "error": doc.get("error")
            }
    except Exception:
        pass

    return None


def _update_job_stage(job_id: str, stage: str, progress: int, status: str = "PROCESSING", error: str = None, result: Dict[str, Any] = None, analysis_id: str = None):
    now = datetime.utcnow()
    with _LOCK:
        if job_id in _ACTIVE_JOBS:
            _ACTIVE_JOBS[job_id]["stage"] = stage
            _ACTIVE_JOBS[job_id]["progress"] = progress
            _ACTIVE_JOBS[job_id]["status"] = status
            _ACTIVE_JOBS[job_id]["updated_at"] = now
            if error:
                _ACTIVE_JOBS[job_id]["error"] = error
            if result:
                _ACTIVE_JOBS[job_id]["result"] = result
            if analysis_id:
                _ACTIVE_JOBS[job_id]["analysis_id"] = analysis_id
            _ACTIVE_JOBS[job_id]["stage_history"].append({
                "stage": stage,
                "status": "COMPLETED" if status == "COMPLETED" else "IN_PROGRESS",
                "timestamp": now.isoformat()
            })

    try:
        jobs_coll = _get_jobs_collection()
        update_fields = {
            "stage": stage,
            "progress": progress,
            "status": status,
            "updated_at": now
        }
        if error:
            update_fields["error"] = error
        if result:
            update_fields["result"] = result
        if analysis_id:
            update_fields["analysis_id"] = analysis_id

        jobs_coll.update_one(
            {"job_id": job_id},
            {
                "$set": update_fields,
                "$push": {"stage_history": {
                    "stage": stage,
                    "status": "COMPLETED" if status == "COMPLETED" else "IN_PROGRESS",
                    "timestamp": now.isoformat()
                }}
            }
        )
    except Exception as e:
        logger.warning(f"Could not update job {job_id} in MongoDB: {e}")


def execute_analysis_job_sync(job_id: str) -> Dict[str, Any]:
    """
    Executes an analysis job synchronously through all phases while updating progress.
    """
    with _LOCK:
        job = _ACTIVE_JOBS.get(job_id)

    if not job:
        try:
            jobs_coll = _get_jobs_collection()
            job = jobs_coll.find_one({"job_id": job_id})
        except Exception:
            pass

    if not job:
        raise ValueError(f"Job {job_id} not found.")

    user_id = job.get("user_id")
    payload = job.get("input_payload", {})

    text = payload.get("text", "")
    metadata = payload.get("metadata", {})
    file_path = payload.get("file_path")
    file_extension = payload.get("file_extension")
    file_info = payload.get("file_info")
    extraction_meta = {}

    try:
        # Stage 1: VALIDATION
        _update_job_stage(job_id, "VALIDATION", 15)

        # Stage 2: OCR / TEXT EXTRACTION
        if file_path and file_extension:
            _update_job_stage(job_id, "OCR", 30)
            extracted_data = extract_text_from_file(file_path, file_extension)
            extracted_text = extracted_data.get("text", "")
            if extracted_text and len(extracted_text.strip()) > 0:
                text = extracted_text
            extraction_meta = extracted_data
            if file_info:
                file_info["extraction_method"] = extracted_data.get("method")
                file_info["is_poor_quality"] = extracted_data.get("is_poor", False)
                file_info["quality_warning"] = extracted_data.get("quality_warning")
                try:
                    get_files_collection().insert_one(file_info)
                except Exception:
                    pass

        # Stage 3: TEXT EXTRACTION & ENTITY EXTRACTION
        _update_job_stage(job_id, "ENTITY_EXTRACTION", 50)
        entities = extract_entities(text, metadata)

        # Stage 4: DOMAIN INTELLIGENCE & URL INTELLIGENCE
        _update_job_stage(job_id, "DOMAIN_INTELLIGENCE", 65)
        domain_intelligence = extract_domain_intelligence(metadata, entities, text)
        url_intelligence = extract_url_intelligence(text, entities.get("company", ""))
        domain_intelligence["extracted_urls"] = url_intelligence

        # Stage 5: LOCAL AI ANALYSIS
        _update_job_stage(job_id, "AI_ANALYSIS", 85)
        metadata["quality_warning"] = extraction_meta.get("quality_warning")
        ai_result = run_semantic_scam_analysis(text=text, metadata=metadata)

        # Stage 6: REPORT GENERATION
        _update_job_stage(job_id, "REPORT_GENERATION", 95)
        document_type = ai_result.get("document_type", "UNKNOWN")
        risk_score = ai_result.get("risk_score", 0)
        confidence = ai_result.get("confidence", 85)
        classification = ai_result.get("classification", "SAFE")
        summary = ai_result.get("summary", "")
        reasoning = ai_result.get("reasoning", [])

        risk_signals = build_forensic_signals(reasoning, document_type)
        ai_opinion = build_ai_opinion(ai_result, text, metadata, entities, domain_intelligence)
        document_intelligence = build_document_intelligence(ai_result, text, file_info)

        # Map display properties
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

        trust_score = max(0, min(100, 100 - risk_score))

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

        pillars = {
            "payment_risk": 100, "identity_risk": 100, "urgency_risk": 100,
            "contact_risk": 100, "company_risk": 100, "language_risk": 100
        }
        for item in reasoning:
            finding = (item.get("finding", "") + " " + item.get("explanation", "")).lower()
            impact = int(item.get("impact_on_score", 15))
            penalty = min(70, impact * 2)
            if any(w in finding for w in ["payment", "fee", "deposit", "money", "crypto"]):
                pillars["payment_risk"] = max(10, pillars["payment_risk"] - penalty)
            if any(w in finding for w in ["identity", "ssn", "passport", "bank"]):
                pillars["identity_risk"] = max(10, pillars["identity_risk"] - penalty)
            if any(w in finding for w in ["urgency", "urgent", "pressure", "immediately"]):
                pillars["urgency_risk"] = max(10, pillars["urgency_risk"] - penalty)
            if any(w in finding for w in ["email", "domain", "contact", "telegram"]):
                pillars["contact_risk"] = max(10, pillars["contact_risk"] - penalty)
            if any(w in finding for w in ["company", "impersonat", "unregistered"]):
                pillars["company_risk"] = max(10, pillars["company_risk"] - penalty)
            if any(w in finding for w in ["grammar", "spelling", "manipulat"]):
                pillars["language_risk"] = max(10, pillars["language_risk"] - penalty)

        analysis_result = {
            "document_type": document_type,
            "document_type_confidence": ai_result.get("document_type_confidence", 80),
            "risk_score": risk_score,
            "trust_score": trust_score,
            "confidence": confidence,
            "classification": classification,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "summary": summary,
            "ai_explanation": summary,
            "reasoning": reasoning,
            "positive_signals": ai_result.get("positive_signals", []),
            "uncertainties": ai_result.get("uncertainties", []),
            "document_assessment": ai_result.get("document_assessment", {}),
            "recommendations": ai_result.get("recommendations", []),
            "structured_red_flags": structured_red_flags,
            "red_flags": legacy_red_flags,
            "risk_breakdown": pillars,
            "risk_signals": risk_signals,
            "entities": entities,
            "domain_intelligence": domain_intelligence,
            "ai_opinion": ai_opinion,
            "document_intelligence": document_intelligence,
            "company_name": metadata.get("company_name") or entities.get("company", "Not Specified"),
            "job_title": metadata.get("job_title") or entities.get("role", "Job Offer"),
            "company_email": metadata.get("company_email") or entities.get("email", ""),
            "company_website": metadata.get("company_website") or domain_intelligence.get("company_website", ""),
            "company_phone": metadata.get("company_phone") or entities.get("phone", ""),
            "job_location": metadata.get("job_location") or entities.get("location", ""),
            "model_name": ai_result.get("model_name", "llama3.2:3b"),
            "extraction_warning": extraction_meta.get("quality_warning"),
            "is_poor_extraction": extraction_meta.get("is_poor", False)
        }

        # Persist analysis
        now = datetime.utcnow()
        analyses_coll = get_analyses_collection()
        db_record = dict(analysis_result)
        db_record["user_id"] = user_id
        db_record["text"] = text[:5000]
        db_record["extracted_text"] = text
        db_record["created_at"] = now
        db_record["analysis_timestamp"] = now

        insert_res = analyses_coll.insert_one(db_record)
        analysis_id = str(insert_res.inserted_id)
        analysis_result["analysis_id"] = analysis_id
        analysis_result["_id"] = analysis_id
        analysis_result["created_at"] = now.isoformat()

        # Mark job COMPLETED
        _update_job_stage(
            job_id,
            stage="COMPLETED",
            progress=100,
            status="COMPLETED",
            result=analysis_result,
            analysis_id=analysis_id
        )

        # In-app notifications & Activity logging
        log_activity(
            user_id=user_id,
            action="analysis_completed",
            details=f"Analyzed {analysis_result['job_title']} at {analysis_result['company_name']} (Risk: {risk_score}/100)"
        )
        create_notification(
            user_id=user_id,
            title=f"Analysis Complete: {risk_level} ({risk_score}/100)",
            message=f"{analysis_result['job_title']} at {analysis_result['company_name']} analyzed via local AI.",
            notif_type=notif_type,
            link=f"result.html?id={analysis_id}"
        )
        log_audit_event(
            event_type="AI_ANALYSIS_COMPLETED",
            user_id=user_id,
            details={"analysis_id": analysis_id, "risk_score": risk_score, "classification": classification}
        )

        # Phase 6 & 7: Check notification preferences and dispatch email
        _dispatch_analysis_notifications(user_id, analysis_id, analysis_result)

        return analysis_result

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        _update_job_stage(job_id, stage="FAILED", progress=0, status="FAILED", error=str(e))
        raise e


def start_analysis_job_async(job_id: str):
    """
    Spawns background worker thread to process job asynchronously.
    """
    thread = threading.Thread(target=execute_analysis_job_sync, args=(job_id,), daemon=True)
    thread.start()


def _dispatch_analysis_notifications(user_id: str, analysis_id: str, analysis_result: Dict[str, Any]):
    """
    Dispatches analysis complete and high-risk alert emails based on user preferences.
    """
    try:
        users_coll = get_users_collection()
        from bson import ObjectId
        user = users_coll.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("email"):
            return

        prefs = user.get("notification_preferences", {})
        analysis_completed_pref = prefs.get("analysis_completed", True)
        high_risk_pref = prefs.get("high_risk_alerts", True)

        risk_score = analysis_result.get("risk_score", 0)
        high_risk_threshold = int(os.getenv("HIGH_RISK_EMAIL_THRESHOLD", "75"))
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5000")

        # Check if should notify
        should_send = False
        if risk_score >= high_risk_threshold and high_risk_pref:
            should_send = True
        elif analysis_completed_pref:
            should_send = True

        if should_send:
            # Build primary indicators from reasoning
            indicators = []
            for r in analysis_result.get("reasoning", [])[:4]:
                if r.get("finding"):
                    indicators.append(r.get("finding"))

            if not indicators:
                indicators = ["Standard forensic baseline analysis completed."]

            send_email(
                to=user["email"],
                template="analysis-complete",
                data={
                    "name": user.get("name", "User"),
                    "risk_score": risk_score,
                    "classification": analysis_result.get("classification", "ANALYSIS COMPLETE"),
                    "confidence": analysis_result.get("confidence", 85),
                    "indicators": indicators,
                    "report_url": f"{frontend_url}/result.html?id={analysis_id}",
                    "document_name": analysis_result.get("job_title", "Document Analysis")
                },
                user_id=user_id,
                async_send=True
            )
            logger.info(f"Dispatched analysis email notification for user {user['email']} (Risk: {risk_score})")

        # Section 50: Outbound Webhook dispatch
        try:
            from backend.webhook_dispatcher import dispatch_webhook_event
            webhook_payload = {
                'analysis_id': analysis_id,
                'risk_score': risk_score,
                'risk_level': analysis_result.get("risk_level", analysis_result.get("classification", "UNKNOWN")),
                'company_name': analysis_result.get("company_name", "Not Specified"),
                'job_title': analysis_result.get("job_title", "Document Analysis"),
                'created_at': datetime.utcnow().isoformat()
            }
            dispatch_webhook_event(user_id, 'analysis.completed', webhook_payload)
            if risk_score >= high_risk_threshold:
                dispatch_webhook_event(user_id, 'analysis.high_risk', webhook_payload)
        except Exception as we:
            logger.warning(f"Webhook event dispatch error: {we}")

    except Exception as e:
        logger.warning(f"Failed to dispatch analysis email notification: {e}")
