"""
ScamGuard AI - Versioned API & Webhooks Blueprint (/api/v1)
Implements:
- Section 49: Versioned API & API Key Management (/api/v1/analyze, /analysis/<id>, /domain/<domain>, /report/<id>)
- Section 50: Webhook Subscriptions & HMAC-SHA256 Signature Verification
"""

import os
import secrets
import hashlib
import json
import requests
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from backend.database import (
    get_api_keys_collection,
    get_webhooks_collection,
    get_webhook_deliveries_collection,
    get_analyses_collection,
    get_users_collection
)
from backend.auth_utils import require_auth, decode_token
from backend.rate_limiter import apply_rate_limit
from backend.forensic_utils import (
    extract_entities,
    extract_domain_intelligence,
    build_forensic_signals,
    build_ai_opinion,
    build_document_intelligence,
    detect_lookalike_domain
)
from backend.ai_analyzer import run_semantic_scam_analysis
from backend.webhook_dispatcher import compute_signature, dispatch_webhook_event

api_v1_bp = Blueprint('api_v1', __name__)

def hash_api_key(raw_key: str) -> str:
    """Computes SHA-256 hash of API key for secure storage."""
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

def require_api_or_jwt(f):
    """
    Decorator allowing programmatic authentication via X-API-Key header
    or Authorization: Bearer JWT.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key', '').strip()
        auth_header = request.headers.get('Authorization', '').strip()

        if api_key:
            # Hash and look up active key
            key_hash = hash_api_key(api_key)
            keys_col = get_api_keys_collection()
            key_doc = keys_col.find_one({'key_hash': key_hash, 'revoked': False}) if keys_col is not None else None

            if not key_doc:
                return jsonify({'error': {'code': 'INVALID_API_KEY', 'message': 'The provided API key is invalid or revoked.'}}), 401

            # Update last_used_at
            now = datetime.utcnow()
            keys_col.update_one({'_id': key_doc['_id']}, {'$set': {'last_used_at': now}})

            request.user_id = str(key_doc['user_id'])
            request.auth_type = 'api_key'
            request.api_key_id = str(key_doc['_id'])

            # Apply rate limit per API key (60 req / min)
            limit_ok, msg = apply_rate_limit(f"apikey:{key_doc['_id']}", limit=60, window_seconds=60)
            if not limit_ok:
                return jsonify({'error': {'code': 'RATE_LIMITED', 'message': msg}}), 429

            return f(*args, **kwargs)

        elif auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1].strip()
            decoded = decode_token(token)
            if not decoded or decoded.get('type') == 'temp_2fa':
                return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid or expired bearer token.'}}), 401

            request.user_id = decoded['user_id']
            request.user_email = decoded.get('email')
            request.user_role = decoded.get('role', 'USER')
            request.auth_type = 'jwt'
            return f(*args, **kwargs)

        return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required. Provide X-API-Key header or Authorization Bearer token.'}}), 401

    return decorated


# ==============================================================================
# SECTION 49: API KEY LIFECYCLE MANAGEMENT
# ==============================================================================

@api_v1_bp.route('/keys', methods=['POST'])
@require_auth
def create_api_key():
    """Generates a secure API key with prefix sg_live_."""
    try:
        data = request.get_json() or {}
        name = data.get('name', 'Default Production Key').strip()

        raw_token = secrets.token_hex(24)
        full_key = f"sg_live_{raw_token}"
        key_hash = hash_api_key(full_key)
        prefix = f"sg_live_{raw_token[:6]}...{raw_token[-4:]}"

        keys_col = get_api_keys_collection()
        now = datetime.utcnow()

        insert_res = keys_col.insert_one({
            'user_id': request.user_id,
            'name': name,
            'key_prefix': prefix,
            'key_hash': key_hash,
            'revoked': False,
            'created_at': now,
            'last_used_at': None
        })

        return jsonify({
            'message': 'API key successfully generated. Copy this key now as it cannot be shown again.',
            'api_key': full_key,
            'id': str(insert_res.inserted_id),
            'key_id': str(insert_res.inserted_id),
            'prefix': prefix,
            'name': name,
            'created_at': now.isoformat()
        }), 201

    except Exception as e:
        return jsonify({'error': {'code': 'KEY_CREATION_FAILED', 'message': str(e)}}), 500


@api_v1_bp.route('/keys', methods=['GET'])
@require_auth
def list_api_keys():
    """Lists all active API keys for the current user."""
    try:
        keys_col = get_api_keys_collection()
        keys = []
        if keys_col is not None:
            cur = keys_col.find({'user_id': request.user_id, 'revoked': False}).sort('created_at', -1)
            for k in cur:
                keys.append({
                    'id': str(k['_id']),
                    'name': k.get('name', 'API Key'),
                    'prefix': k.get('key_prefix'),
                    'created_at': k.get('created_at').isoformat() if k.get('created_at') else None,
                    'last_used_at': k.get('last_used_at').isoformat() if k.get('last_used_at') else None
                })

        return jsonify({'keys': keys}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'KEY_LIST_FAILED', 'message': str(e)}}), 500


@api_v1_bp.route('/keys/<key_id>', methods=['DELETE'])
@require_auth
def revoke_api_key(key_id):
    """Revokes an API key."""
    try:
        keys_col = get_api_keys_collection()
        if keys_col is not None:
            doc_filter = {'_id': ObjectId(str(key_id))} if ObjectId.is_valid(str(key_id)) else {'_id': str(key_id)}
            doc_filter['user_id'] = request.user_id
            res = keys_col.update_one(
                doc_filter,
                {'$set': {'revoked': True, 'revoked_at': datetime.utcnow()}}
            )
            if res.matched_count == 0:
                return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'API key not found.'}}), 404

        return jsonify({'message': 'API key revoked successfully.'}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'KEY_REVOKE_FAILED', 'message': str(e)}}), 500


# ==============================================================================
# SECTION 49: VERSIONED ENDPOINTS (/api/v1/...)
# ==============================================================================

@api_v1_bp.route('/analyze', methods=['POST'])
@require_api_or_jwt
def api_analyze():
    """
    Versioned programmatic analysis endpoint.
    Accepts raw text or URL payload, runs full forensic AI analysis,
    persists record, and dispatches webhooks.
    """
    try:
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        company_name = data.get('company_name', '').strip()
        job_title = data.get('job_title', '').strip()

        if not text:
            return jsonify({'error': {'code': 'MISSING_TEXT', 'message': 'Document text is required for analysis.'}}), 400

        user_id = request.user_id
        analysis_result = run_semantic_scam_analysis(text, company_name=company_name, job_title=job_title)

        doc_intel = build_document_intelligence(text)
        entities = extract_entities(text, company_name, job_title)
        domain_intel = extract_domain_intelligence(text, entities)
        signals = build_forensic_signals(analysis_result, entities, domain_intel)
        ai_opinion = build_ai_opinion(analysis_result, entities, domain_intel, doc_intel)

        risk_score = analysis_result.get('risk_score', 0)
        risk_level = analysis_result.get('risk_level', 'LOW_RISK')

        now = datetime.utcnow()
        col = get_analyses_collection()

        record = {
            'user_id': user_id,
            'company_name': company_name or entities.get('company_name', 'Not Specified'),
            'job_title': job_title or entities.get('job_title', 'Not Specified'),
            'risk_score': risk_score,
            'risk_level': risk_level,
            'trust_score': 100 - risk_score,
            'confidence': analysis_result.get('confidence', 90),
            'document_type': doc_intel.get('document_type', 'GENERAL_DOCUMENT'),
            'red_flags': analysis_result.get('red_flags', []),
            'structured_red_flags': analysis_result.get('structured_red_flags', []),
            'positive_signals': analysis_result.get('positive_signals', []),
            'uncertainties': analysis_result.get('uncertainties', []),
            'recommendations': analysis_result.get('recommendations', []),
            'entities': entities,
            'domain_intelligence': domain_intel,
            'risk_signals': signals,
            'ai_opinion': ai_opinion,
            'document_intelligence': doc_intel,
            'model_name': analysis_result.get('model_name', 'llama3.2:3b'),
            'source_channel': f"api_v1_{getattr(request, 'auth_type', 'jwt')}",
            'created_at': now
        }

        insert_res = col.insert_one(record)
        analysis_id = str(insert_res.inserted_id)

        # Dispatch webhooks
        event_payload = {
            'analysis_id': analysis_id,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'classification': risk_level,
            'company_name': record['company_name'],
            'job_title': record['job_title'],
            'created_at': now.isoformat()
        }
        dispatch_webhook_event(user_id, 'analysis.completed', event_payload)
        if risk_score >= 70:
            dispatch_webhook_event(user_id, 'analysis.high_risk', event_payload)

        return jsonify({
            'status': 'success',
            'analysis_id': analysis_id,
            'risk_score': risk_score,
            'classification': risk_level,
            'confidence': record['confidence'],
            'document_type': record['document_type'],
            'entities': entities,
            'forensic_signals': signals,
            'ai_opinion': ai_opinion,
            'created_at': now.isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': {'code': 'ANALYSIS_ERROR', 'message': str(e)}}), 500


@api_v1_bp.route('/analysis/<analysis_id>', methods=['GET'])
@require_api_or_jwt
def api_get_analysis(analysis_id):
    """Retrieves full analysis document by ID."""
    try:
        col = get_analyses_collection()
        doc = col.find_one({'_id': ObjectId(analysis_id)})
        if not doc:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Analysis not found.'}}), 404

        role = getattr(request, 'user_role', 'USER')
        if role != 'ADMIN' and str(doc.get('user_id')) != request.user_id:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Unauthorized.'}}), 403

        doc['id'] = str(doc.pop('_id'))
        if hasattr(doc.get('created_at'), 'isoformat'):
            doc['created_at'] = doc['created_at'].isoformat()

        return jsonify({'analysis': doc}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'FETCH_ERROR', 'message': str(e)}}), 500


@api_v1_bp.route('/domain/<domain_name>', methods=['GET'])
@require_api_or_jwt
def api_get_domain(domain_name):
    """Retrieves domain intelligence, lookalike checks, and TLS/DNS records."""
    try:
        clean_domain = domain_name.strip().lower()
        lookalike = detect_lookalike_domain(clean_domain)
        mock_meta = {'company_website': f"https://{clean_domain}"}
        intel = extract_domain_intelligence(metadata=mock_meta, entities={'company': clean_domain})

        return jsonify({
            'domain': clean_domain,
            'domain_intelligence': intel,
            'lookalike_detection': lookalike
        }), 200
    except Exception as e:
        return jsonify({'error': {'code': 'DOMAIN_LOOKUP_ERROR', 'message': str(e)}}), 500


@api_v1_bp.route('/report/<analysis_id>', methods=['GET'])
@require_api_or_jwt
def api_get_report(analysis_id):
    """Retrieves exportable report JSON."""
    return api_get_analysis(analysis_id)


# ==============================================================================
# SECTION 50: WEBHOOKS MANAGEMENT
# ==============================================================================

@api_v1_bp.route('/webhooks', methods=['POST'])
@require_auth
def create_webhook():
    """Registers an outbound webhook destination with HMAC signing secret."""
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()
        events = data.get('events', ['analysis.completed', 'analysis.high_risk'])

        if not url or not (url.startswith('http://') or url.startswith('https://')):
            return jsonify({'error': {'code': 'INVALID_URL', 'message': 'A valid HTTP/HTTPS webhook URL is required.'}}), 400

        secret = data.get('secret', secrets.token_hex(16))
        webhooks_col = get_webhooks_collection()
        now = datetime.utcnow()

        insert_res = webhooks_col.insert_one({
            'user_id': request.user_id,
            'url': url,
            'events': events,
            'secret': secret,
            'active': True,
            'created_at': now
        })

        return jsonify({
            'message': 'Webhook successfully registered.',
            'id': str(insert_res.inserted_id),
            'webhook_id': str(insert_res.inserted_id),
            'url': url,
            'events': events,
            'secret': secret,
            'created_at': now.isoformat()
        }), 201

    except Exception as e:
        return jsonify({'error': {'code': 'WEBHOOK_CREATION_FAILED', 'message': str(e)}}), 500


@api_v1_bp.route('/webhooks', methods=['GET'])
@require_auth
def list_webhooks():
    """Lists registered webhooks for the user."""
    try:
        webhooks_col = get_webhooks_collection()
        hooks = []
        if webhooks_col is not None:
            cur = webhooks_col.find({'user_id': request.user_id}).sort('created_at', -1)
            for h in cur:
                hooks.append({
                    'id': str(h['_id']),
                    'url': h.get('url'),
                    'events': h.get('events', []),
                    'active': h.get('active', True),
                    'created_at': h.get('created_at').isoformat() if h.get('created_at') else None
                })
        return jsonify({'webhooks': hooks}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'WEBHOOK_LIST_FAILED', 'message': str(e)}}), 500


@api_v1_bp.route('/webhooks/<webhook_id>', methods=['DELETE'])
@require_auth
def delete_webhook(webhook_id):
    """Deletes a registered webhook."""
    try:
        webhooks_col = get_webhooks_collection()
        if webhooks_col is not None:
            doc_filter = {'_id': ObjectId(str(webhook_id))} if ObjectId.is_valid(str(webhook_id)) else {'_id': str(webhook_id)}
            doc_filter['user_id'] = request.user_id
            res = webhooks_col.delete_one(doc_filter)
            if res.deleted_count == 0:
                return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Webhook not found.'}}), 404
        return jsonify({'message': 'Webhook deleted successfully.'}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'WEBHOOK_DELETE_FAILED', 'message': str(e)}}), 500


@api_v1_bp.route('/webhooks/<webhook_id>/test', methods=['POST'])
@require_auth
def test_webhook(webhook_id):
    """Dispatches a signed test ping to verify webhook receipt."""
    try:
        webhooks_col = get_webhooks_collection()
        if webhooks_col is None:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Webhook database unavailable.'}}), 503

        doc_filter = {'_id': ObjectId(str(webhook_id))} if ObjectId.is_valid(str(webhook_id)) else {'_id': str(webhook_id)}
        doc_filter['user_id'] = request.user_id
        hook = webhooks_col.find_one(doc_filter)
        if not hook:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Webhook not found.'}}), 404

        url = hook.get('url')
        secret = hook.get('secret', '')
        test_payload = {
            'event': 'test.ping',
            'timestamp': int(datetime.utcnow().timestamp()),
            'data': {
                'message': 'ScamGuard AI forensic webhook delivery test ping.',
                'webhook_id': str(webhook_id)
            }
        }
        body_bytes = json.dumps(test_payload, default=str).encode('utf-8')
        sig = f"sha256={compute_signature(body_bytes, secret)}"

        status_code = 200
        try:
            import requests
            resp = requests.post(url, data=body_bytes, headers={
                'Content-Type': 'application/json',
                'X-ScamGuard-Signature': sig,
                'X-ScamGuard-Event': 'test.ping'
            }, timeout=10)
            status_code = int(resp.status_code) if isinstance(resp.status_code, (int, float)) else 200
        except Exception:
            status_code = 500

        return jsonify({'message': 'Test webhook event dispatched.', 'status_code': status_code}), 200
    except Exception as e:
        return jsonify({'error': {'code': 'TEST_DISPATCH_FAILED', 'message': str(e)}}), 500
