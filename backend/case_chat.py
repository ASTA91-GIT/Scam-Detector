"""
CaseAI API Blueprint
Exposes endpoints for case-aware chat, SSE streaming, case context,
actions, history, and exports.
"""
import json
from flask import Blueprint, request, jsonify, Response, stream_with_context
from backend.auth_utils import require_auth
from backend.ai.chat_service import CaseAIChatService
from backend.ai.provider_factory import get_ai_status
from backend.database import get_analyses_collection

case_chat_bp = Blueprint('case_chat', __name__)

@case_chat_bp.route('/cases/<case_id>/chat', methods=['POST'])
@require_auth
def chat_sync_endpoint(case_id):
    """Synchronous chat endpoint returning complete response JSON"""
    try:
        user_id = request.user_id
        data = request.get_json() or {}
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "Message is required."}), 400

        result = CaseAIChatService.chat_sync(case_id, user_id, message)
        return jsonify(result), 200
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Chat processing failed: {str(e)}"}), 500


@case_chat_bp.route('/cases/<case_id>/chat/stream', methods=['POST'])
@require_auth
def chat_stream_endpoint(case_id):
    """Server-Sent Events (SSE) streaming chat endpoint"""
    try:
        user_id = request.user_id
        data = request.get_json() or {}
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "Message is required."}), 400

        # Pre-verify case permission before starting stream
        CaseAIChatService.get_case_context_data(case_id, user_id)

        def generate():
            try:
                for chunk in CaseAIChatService.stream_chat(case_id, user_id, message):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as stream_err:
                yield f"data: {json.dumps({'error': str(stream_err)})}\n\n"
                yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to initialize stream: {str(e)}"}), 500


@case_chat_bp.route('/cases/<case_id>/chat/action', methods=['POST'])
@require_auth
def chat_action_endpoint(case_id):
    """Runs a predefined investigation action (explain, investigate, checklist, recruiter_questions, summary) with SSE streaming"""
    try:
        user_id = request.user_id
        data = request.get_json() or {}
        action = data.get("action", "").strip().lower()

        if not action:
            return jsonify({"error": "Action name is required."}), 400

        # Pre-verify permissions
        CaseAIChatService.get_case_context_data(case_id, user_id)

        def generate():
            try:
                for chunk in CaseAIChatService.execute_special_action(case_id, user_id, action):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as err:
                yield f"data: {json.dumps({'error': str(err)})}\n\n"
                yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": f"Action failed: {str(e)}"}), 500


@case_chat_bp.route('/cases/<case_id>/chat/history', methods=['GET'])
@require_auth
def chat_history_endpoint(case_id):
    """Fetch conversation messages for a case"""
    try:
        user_id = request.user_id
        history = CaseAIChatService.get_history(case_id, user_id)
        return jsonify(history), 200
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@case_chat_bp.route('/cases/<case_id>/chat/context', methods=['GET'])
@require_auth
def chat_context_endpoint(case_id):
    """Fetch structured case context, evidence, and important facts"""
    try:
        user_id = request.user_id
        context = CaseAIChatService.get_case_context_data(case_id, user_id)
        return jsonify({"case_context": context}), 200
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@case_chat_bp.route('/cases/<case_id>/chat', methods=['DELETE'])
@require_auth
def clear_chat_endpoint(case_id):
    """Reset and clear conversation history for a case"""
    try:
        user_id = request.user_id
        res = CaseAIChatService.clear_history(case_id, user_id)
        return jsonify(res), 200
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@case_chat_bp.route('/cases/<case_id>/chat/export', methods=['GET'])
@require_auth
def export_chat_endpoint(case_id):
    """Export conversation transcript as text or JSON"""
    try:
        user_id = request.user_id
        fmt = request.args.get("format", "txt").lower()
        res = CaseAIChatService.export_chat(case_id, user_id, export_format=fmt)
        return jsonify(res), 200
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@case_chat_bp.route('/ai/status', methods=['GET'])
def ai_status_endpoint():
    """Public diagnostics for AI engine and local Ollama state"""
    status = get_ai_status()
    return jsonify(status), 200


@case_chat_bp.route('/cases/recent', methods=['GET'])
@require_auth
def recent_cases_endpoint():
    """Retrieve recent analyses for the global case-switcher"""
    try:
        user_id = request.user_id
        col = get_analyses_collection()
        docs = list(col.find({"user_id": user_id}).sort("created_at", -1).limit(10))
        cases = []
        for d in docs:
            cases.append({
                "id": str(d["_id"]),
                "company_name": d.get("company_name", "Unknown Company"),
                "job_title": d.get("job_title", "Job Offer"),
                "risk_level": d.get("risk_level", "Unknown"),
                "risk_score": 100 - d.get("trust_score", 50),
                "created_at": d.get("created_at").isoformat() if hasattr(d.get("created_at"), "isoformat") else str(d.get("created_at"))
            })
        return jsonify({"cases": cases}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
