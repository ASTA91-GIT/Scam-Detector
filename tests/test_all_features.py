"""
End-to-End Verification Test Script
Tests all newly created backend endpoints and flows.
"""
import unittest
import json
from app import app
from backend.database import get_db

class TestScamDetectorE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        cls.test_email = f"qa_analyst_{int(__import__('time').time())}@example.com"
        cls.test_password = "SecurePassword123!#"
        cls.test_username = "QA Lead Analyst"
        cls.token = None
        cls.analysis_id = None
        cls.saved_id = None

    def test_01_signup(self):
        res = self.client.post('/api/auth/signup', json={
            'username': self.test_username,
            'email': self.test_email,
            'password': self.test_password
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn('token', data)
        self.assertIn('user', data)
        TestScamDetectorE2E.token = data['token']
        print("[TEST PASS] 01: Signup & user creation")

    def test_02_login(self):
        res = self.client.post('/api/auth/login', json={
            'email': self.test_email,
            'password': self.test_password
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('token', data)
        print("[TEST PASS] 02: Login & JWT token issue")

    def test_03_profile(self):
        res = self.client.get('/api/auth/profile', headers={
            'Authorization': f'Bearer {self.token}'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['email'], self.test_email)
        self.assertEqual(data['username'], self.test_username)
        print("[TEST PASS] 03: Profile retrieval")

    def test_04_analysis_execute(self):
        sample_scam = (
            "URGENT: Guaranteed $500 daily for remote data processing. "
            "No interview required! Deposit 100 USDT into crypto wallet to verify account. "
            "Act ASAP or position expires today! Reply on Telegram immediately."
        )
        res = self.client.post('/api/analysis/analyze', headers={
            'Authorization': f'Bearer {self.token}'
        }, json={
            'text': sample_scam,
            'company_name': 'Scam Tasks Corp',
            'job_title': 'Crypto Order Specialist',
            'company_email': 'hr.fraud@gmail.com',
            'company_website': 'https://fake-tasks-reward.xyz'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        result = data.get('result', {})
        self.assertEqual(result.get('risk_level'), 'High Risk')
        self.assertTrue(result.get('trust_score') < 50)
        self.assertTrue(len(result.get('structured_red_flags', [])) > 0)
        TestScamDetectorE2E.analysis_id = result.get('analysis_id')
        self.assertIsNotNone(TestScamDetectorE2E.analysis_id)
        print(f"[TEST PASS] 04: Analysis executed (Score: {result.get('trust_score')}, Flags: {len(result.get('structured_red_flags'))})")

    def test_05_analysis_get_by_id(self):
        res = self.client.get(f'/api/analysis/result/{self.analysis_id}', headers={
            'Authorization': f'Bearer {self.token}'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('analysis', data)
        self.assertEqual(data['analysis']['risk_level'], 'High Risk')
        print("[TEST PASS] 05: Get analysis result by ID")

    def test_06_url_scan(self):
        res = self.client.post('/api/analysis/scan-url', headers={
            'Authorization': f'Bearer {self.token}'
        }, json={
            'url': 'http://portal-login-verify.top/auth',
            'company_name': 'Google'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('scan', data)
        print(f"[TEST PASS] 06: URL Scanner evaluated (Risk: {data['scan']['risk_level']})")

    def test_07_dashboard_stats(self):
        res = self.client.get('/api/dashboard/stats', headers={
            'Authorization': f'Bearer {self.token}'
        })
        self.assertEqual(res.status_code, 200)
        stats = res.get_json()
        self.assertGreaterEqual(stats['total_analyses'], 1)
        self.assertGreaterEqual(stats['high_risk_count'], 1)
        print(f"[TEST PASS] 07: Dashboard stats (Total: {stats['total_analyses']}, Safety Score: {stats['safety_score']})")

    def test_08_save_report(self):
        res = self.client.post('/api/saved-reports', headers={
            'Authorization': f'Bearer {self.token}'
        }, json={
            'analysis_id': self.analysis_id,
            'custom_title': 'Suspicious Crypto Re-shipping Offer Investigation',
            'notes': 'Telegram user @HR_FastCryptoRecruit asked for deposit.'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        TestScamDetectorE2E.saved_id = data.get('saved_id')
        self.assertIsNotNone(TestScamDetectorE2E.saved_id)
        print("[TEST PASS] 08: Save report & investigator notes")

    def test_09_check_saved(self):
        res = self.client.get(f'/api/saved-reports/check/{self.analysis_id}', headers={
            'Authorization': f'Bearer {self.token}'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['is_saved'])
        print("[TEST PASS] 09: Check saved status")

    def test_10_notifications(self):
        res = self.client.get('/api/notifications', headers={
            'Authorization': f'Bearer {self.token}'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(len(data['notifications']), 1)
        print(f"[TEST PASS] 10: Notifications retrieved (Count: {len(data['notifications'])})")

    def test_11_activity_log(self):
        res = self.client.get('/api/auth/activity', headers={
            'Authorization': f'Bearer {self.token}'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(len(data['activity']), 1)
        print(f"[TEST PASS] 11: Activity log audited (Entries: {len(data['activity'])})")

    def test_12_preferences(self):
        res = self.client.put('/api/auth/preferences', headers={
            'Authorization': f'Bearer {self.token}'
        }, json={
            'theme': 'light',
            'email_notifications': False
        })
        self.assertEqual(res.status_code, 200)
        print("[TEST PASS] 12: Preferences updated")

    def test_13_export_data(self):
        res = self.client.get('/api/auth/export-data', headers={
            'Authorization': f'Bearer {self.token}'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('account', data)
        self.assertIn('analyses', data)
        self.assertIn('saved_reports', data)
        print("[TEST PASS] 13: GDPR data export generated")

if __name__ == '__main__':
    unittest.main()
