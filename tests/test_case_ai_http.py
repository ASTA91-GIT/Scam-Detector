"""
Live CaseAI HTTP Endpoints Verification
"""
import requests

BASE = "http://127.0.0.1:5000/api"

def test_endpoints():
    print("Testing CaseAI HTTP Endpoints...")
    # 1. AI Status
    res = requests.get(f"{BASE}/ai/status")
    assert res.status_code == 200
    status_data = res.json()
    print("[OK] AI Status:", status_data["active_provider"])

    # 2. Login or Register
    test_email = "caseai_tester@sentinelscan.io"
    test_pwd = "Password123!"

    login_res = requests.post(f"{BASE}/auth/login", json={
        "email": test_email,
        "password": test_pwd
    })

    if login_res.status_code != 200:
        # Register user
        reg_res = requests.post(f"{BASE}/auth/signup", json={
            "username": "CaseAI Analyst",
            "email": test_email,
            "password": test_pwd
        })
        login_res = requests.post(f"{BASE}/auth/login", json={
            "email": test_email,
            "password": test_pwd
        })

    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Login successful, token obtained.")

    # 3. Get recent cases
    cases_res = requests.get(f"{BASE}/cases/recent", headers=headers)
    assert cases_res.status_code == 200
    cases = cases_res.json().get("cases", [])
    print(f"[OK] Fetched {len(cases)} recent user cases.")

    if not cases:
        print("Creating a sample analysis first...")
        sample_analysis = requests.post(f"{BASE}/analysis/analyze", headers=headers, json={
            "text": "Apex Global is hiring remote data entry clerks. Registration fee of $250 required before laptop dispatch.",
            "company_name": "Apex Global",
            "job_title": "Data Entry"
        })
        case_id = sample_analysis.json()["result"]["analysis_id"]
    else:
        case_id = cases[0]["id"]

    print(f"[OK] Testing with Case ID: {case_id}")

    # 4. Context endpoint
    ctx_res = requests.get(f"{BASE}/cases/{case_id}/chat/context", headers=headers)
    assert ctx_res.status_code == 200
    ctx_data = ctx_res.json()["case_context"]
    print(f"[OK] Context loaded for company: {ctx_data['company']['name']}, Risk: {ctx_data['risk_level']}")

    # 5. Synchronous Chat
    chat_res = requests.post(f"{BASE}/cases/{case_id}/chat", headers=headers, json={
        "message": "Why is this job considered risky?"
    })
    assert chat_res.status_code == 200
    reply = chat_res.json().get("reply", "")
    assert len(reply) > 20
    print(f"[OK] Synchronous Chat response received ({len(reply)} chars).")

    # 6. Streaming Chat (SSE)
    stream_res = requests.post(f"{BASE}/cases/{case_id}/chat/stream", headers=headers, json={
        "message": "What are the biggest red flags in this case?"
    }, stream=True)
    assert stream_res.status_code == 200
    sse_lines = [line.decode("utf-8") for line in stream_res.iter_lines() if line]
    assert len(sse_lines) > 5
    assert any("[DONE]" in l for l in sse_lines)
    print(f"[OK] Streaming Chat SSE verified ({len(sse_lines)} stream chunks received).")

    # 7. Special Action (Checklist)
    action_res = requests.post(f"{BASE}/cases/{case_id}/chat/action", headers=headers, json={
        "action": "checklist"
    }, stream=True)
    assert action_res.status_code == 200
    action_lines = [line.decode("utf-8") for line in action_res.iter_lines() if line]
    assert len(action_lines) > 5
    print(f"[OK] Special Action (Checklist) SSE stream verified ({len(action_lines)} chunks).")

    # 8. Chat History
    hist_res = requests.get(f"{BASE}/cases/{case_id}/chat/history", headers=headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    print(f"[OK] Conversation History verified: {hist_data['count']} persistent messages in MongoDB.")

    # 9. Export
    export_res = requests.get(f"{BASE}/cases/{case_id}/chat/export?format=txt", headers=headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert "content" in export_data
    assert "filename" in export_data
    print(f"[OK] Transcript Export verified: {export_data['filename']}")

    # 10. Global Mode Test
    global_res = requests.get(f"{BASE}/cases/global/chat/context", headers=headers)
    assert global_res.status_code == 200
    assert global_res.json()["case_context"]["is_global"] is True
    print("[OK] Global Assistant mode verified.")

    print("\nALL CASEAI LIVE HTTP TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_endpoints()
