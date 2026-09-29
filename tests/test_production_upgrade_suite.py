"""
Tests for Master Production Upgrades:
- Two-Factor Authentication (TOTP + Recovery codes)
- Analysis Comparison Endpoint
- What-If Risk Simulation
- Recommended Actions Checklist Persistence
- Developer API v1 Key Management & Header Authentication
- Webhook Registration, Signing & Delivery
"""

import pytest
import os
import sys
import json
import uuid
import hmac
import hashlib
import pyotp
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from backend.database import (
    get_users_collection,
    get_analyses_collection,
    get_api_keys_collection,
    get_webhooks_collection,
    get_webhook_deliveries_collection
)
from backend.webhook_dispatcher import sign_webhook_payload, dispatch_webhook_event


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_user(client):
    """Creates a temporary test user and returns credentials and JWT token."""
    email = f"upgrade_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword@123"
    name = "Upgrade Tester"

    reg_res = client.post('/api/auth/register', json={
        'name': name,
        'email': email,
        'password': password
    })
    assert reg_res.status_code in [200, 201]

    # Verify email directly in DB
    users_col = get_users_collection()
    users_col.update_one({'email': email}, {'$set': {'email_verified': True}})

    login_res = client.post('/api/auth/login', json={
        'email': email,
        'password': password
    })
    token = login_res.json.get('token')
    user_id = login_res.json.get('user', {}).get('id')

    return {
        'email': email,
        'password': password,
        'token': token,
        'user_id': user_id,
        'headers': {'Authorization': f'Bearer {token}'}
    }


# ============================================================
# 1. TWO-FACTOR AUTHENTICATION (2FA) TESTS
# ============================================================

def test_2fa_setup_and_verify_flow(client, test_user):
    headers = test_user['headers']

    # 1. Initiate 2FA Setup
    setup_res = client.post('/api/auth/2fa/setup', headers=headers)
    assert setup_res.status_code == 200
    setup_data = setup_res.json
    assert 'secret' in setup_data
    assert 'otpauth_url' in setup_data
    assert 'recovery_codes' in setup_data
    assert len(setup_data['recovery_codes']) == 6

    secret = setup_data['secret']
    recovery_code = setup_data['recovery_codes'][0]

    # 2. Invalid code should fail verification
    bad_verify = client.post('/api/auth/2fa/verify', headers=headers, json={'code': '000000'})
    assert bad_verify.status_code == 400

    # 3. Valid TOTP code verifies and enables 2FA
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    verify_res = client.post('/api/auth/2fa/verify', headers=headers, json={'code': valid_code})
    assert verify_res.status_code == 200
    assert verify_res.json.get('two_factor_enabled') is True

    # 4. Login now requires 2FA challenge
    login_res = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    assert login_res.status_code == 200
    login_data = login_res.json
    assert login_data.get('require_2fa') is True
    temp_token = login_data.get('temp_token')
    assert temp_token is not None

    # 5. Complete login via TOTP code
    totp_login = client.post('/api/auth/login/2fa', json={
        'temp_token': temp_token,
        'code': totp.now()
    })
    assert totp_login.status_code == 200
    assert 'token' in totp_login.json
    assert totp_login.json.get('user', {}).get('two_factor_enabled') is True

    # 6. Disable 2FA
    disable_res = client.post('/api/auth/2fa/disable', headers=headers, json={
        'password': test_user['password']
    })
    assert disable_res.status_code == 200
    assert disable_res.json.get('two_factor_enabled') is False


def test_2fa_login_via_recovery_code(client, test_user):
    headers = test_user['headers']

    # Setup 2FA
    setup_res = client.post('/api/auth/2fa/setup', headers=headers)
    secret = setup_res.json['secret']
    recovery_code = setup_res.json['recovery_codes'][0]

    # Verify and activate
    totp = pyotp.TOTP(secret)
    client.post('/api/auth/2fa/verify', headers=headers, json={'code': totp.now()})

    # Trigger login
    login_res = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    temp_token = login_res.json.get('temp_token')

    # Login using single-use recovery code
    recov_login = client.post('/api/auth/login/2fa', json={
        'temp_token': temp_token,
        'recovery_code': recovery_code
    })
    assert recov_login.status_code == 200
    assert 'token' in recov_login.json

    # Recovery code must be single-use (attempting to reuse should fail)
    login_res2 = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    temp_token2 = login_res2.json.get('temp_token')
    reuse_fail = client.post('/api/auth/login/2fa', json={
        'temp_token': temp_token2,
        'recovery_code': recovery_code
    })
    assert reuse_fail.status_code in [400, 401]


# ============================================================
# 2. ANALYSIS COMPARISON & SIMULATION TESTS
# ============================================================

def test_analysis_comparison_endpoint(client, test_user):
    headers = test_user['headers']
    col = get_analyses_collection()

    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())

    col.insert_one({
        '_id': id1,
        'user_id': test_user['user_id'],
        'company_name': 'Acme Corp',
        'risk_score': 30,
        'risk_level': 'Safe',
        'extracted_entities': {'company': 'Acme Corp', 'salary': '$100k'},
        'findings': ['Standard interview requirement'],
        'red_flags': []
    })

    col.insert_one({
        '_id': id2,
        'user_id': test_user['user_id'],
        'company_name': 'Scammy Tech',
        'risk_score': 85,
        'risk_level': 'High Risk',
        'extracted_entities': {'company': 'Scammy Tech', 'salary': '$250k', 'payment': 'Wire $500'},
        'findings': ['Payment requested upfront', 'Urgency language'],
        'red_flags': ['Wire transfer demand']
    })

    res = client.get(f'/api/analysis/compare?id1={id1}&id2={id2}', headers=headers)
    assert res.status_code == 200
    data = res.json
    assert data['score1'] == 30
    assert data['score2'] == 85
    assert data['score_diff'] == 55
    assert data['classification_changed'] is True
    assert 'salary' in data['changed_entities']
    assert len(data['added_findings']) > 0


def test_what_if_risk_simulation_does_not_mutate_db(client, test_user):
    headers = test_user['headers']
    col = get_analyses_collection()

    doc_id = str(uuid.uuid4())
    initial_score = 25
    col.insert_one({
        '_id': doc_id,
        'user_id': test_user['user_id'],
        'company_name': 'Original Corp',
        'risk_score': initial_score,
        'risk_level': 'Safe',
        'findings': ['Standard contract']
    })

    # Run simulation with fee + urgency
    sim_res = client.post(f'/api/analysis/{doc_id}/simulate', headers=headers, json={
        'scenarios': [
            {'type': 'advance_fee', 'fee_amount': '₹5,000'},
            {'type': 'urgency'}
        ]
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.json
    assert sim_data['simulation'] is True
    assert sim_data['simulated_score'] > initial_score
    assert len(sim_data['hypothetical_findings']) >= 2

    # Verify original document in MongoDB was NOT modified
    saved_doc = col.find_one({'_id': doc_id})
    assert saved_doc['risk_score'] == initial_score
    assert saved_doc['risk_level'] == 'Safe'


# ============================================================
# 3. RECOMMENDED ACTIONS CHECKLIST TESTS
# ============================================================

def test_checklist_get_and_patch(client, test_user):
    headers = test_user['headers']
    col = get_analyses_collection()

    doc_id = str(uuid.uuid4())
    col.insert_one({
        '_id': doc_id,
        'user_id': test_user['user_id'],
        'recommended_actions': [
            'Verify company registration',
            'Do not send money or banking credentials'
        ]
    })

    # GET checklist
    get_res = client.get(f'/api/analysis/{doc_id}/checklist', headers=headers)
    assert get_res.status_code == 200
    items = get_res.json['checklist']
    assert len(items) == 2
    assert items[0]['completed'] is False

    # PATCH checklist item 0 to completed
    patch_res = client.patch(f'/api/analysis/{doc_id}/checklist', headers=headers, json={
        'index': 0,
        'completed': True
    })
    assert patch_res.status_code == 200
    assert patch_res.json['checklist'][0]['completed'] is True
    assert patch_res.json['completed_count'] == 1


# ============================================================
# 4. DEVELOPER API V1 & API KEY AUTHENTICATION
# ============================================================

def test_api_v1_key_lifecycle_and_authentication(client, test_user):
    headers = test_user['headers']

    # 1. Create API Key
    create_res = client.post('/api/v1/keys', headers=headers, json={
        'name': 'CI/CD Pipeline Key'
    })
    assert create_res.status_code == 201
    key_data = create_res.json
    raw_api_key = key_data.get('api_key')
    key_id = key_data.get('id')
    assert raw_api_key.startswith('sg_live_') or raw_api_key.startswith('scamguard_live_')

    # 2. Access /api/v1/keys list (raw key should never be returned, only prefix)
    list_res = client.get('/api/v1/keys', headers=headers)
    assert list_res.status_code == 200
    keys = list_res.json['keys']
    assert any(k['id'] == key_id for k in keys)
    for k in keys:
        assert 'raw_key' not in k

    # 3. Authenticate to /api/v1/domain using X-API-Key
    domain_res = client.get('/api/v1/domain/google.com', headers={
        'X-API-Key': raw_api_key
    })
    assert domain_res.status_code == 200
    assert domain_res.json.get('domain') == 'google.com'

    # 4. Delete API Key
    del_res = client.delete(f'/api/v1/keys/{key_id}', headers=headers)
    assert del_res.status_code == 200

    # 5. Revoked key must fail authentication
    revoked_res = client.get('/api/v1/domain/google.com', headers={
        'X-API-Key': raw_api_key
    })
    assert revoked_res.status_code == 401


# ============================================================
# 5. WEBHOOK REGISTRATION, SIGNING & DELIVERY
# ============================================================

def test_webhook_registration_and_signature(client, test_user):
    headers = test_user['headers']

    # 1. Register Webhook
    reg_res = client.post('/api/v1/webhooks', headers=headers, json={
        'url': 'https://httpbin.org/post',
        'events': ['analysis.completed', 'analysis.high_risk']
    })
    assert reg_res.status_code == 201
    wh_data = reg_res.json
    wh_id = wh_data.get('id')
    secret = wh_data.get('secret')
    assert secret is not None

    # 2. Verify HMAC Signature Generation
    test_payload = json.dumps({'event': 'analysis.completed', 'risk_score': 90}, sort_keys=True)
    signature = sign_webhook_payload(secret, test_payload)
    expected_sig = hmac.new(secret.encode('utf-8'), test_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    assert signature == f"sha256={expected_sig}"

    # 3. Test Webhook Ping with mocked requests.post
    with patch('requests.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text='OK')
        ping_res = client.post(f'/api/v1/webhooks/{wh_id}/test', headers=headers)
        assert ping_res.status_code == 200, f"Error payload: {ping_res.get_json()}"
        assert mock_post.called
        # Verify X-ScamGuard-Signature header was sent
        call_headers = mock_post.call_args[1].get('headers', {})
        assert 'X-ScamGuard-Signature' in call_headers

    # 4. Delete Webhook
    del_wh = client.delete(f'/api/v1/webhooks/{wh_id}', headers=headers)
    assert del_wh.status_code == 200
