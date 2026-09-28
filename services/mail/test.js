const { sendEmail, renderTemplate } = require('./src/mailer');

async function runTest() {
  console.log('Testing template rendering...');
  const templates = [
    'welcome',
    'verify-email',
    'password-reset',
    'security-alert',
    'analysis-complete',
    'report-share',
    'account-deleted'
  ];

  for (const t of templates) {
    const html = renderTemplate(t, {
      username: 'TestAnalyst',
      verification_url: 'http://localhost:5000/verify.html?token=test',
      reset_url: 'http://localhost:5000/reset.html?token=test',
      security_center_url: 'http://localhost:5000/settings.html#security',
      login_url: 'http://localhost:5000/login.html',
      report_url: 'http://localhost:5000/result.html?id=123',
      share_url: 'http://localhost:5000/shared/report/xyz',
      case_id: 'DFDE4415',
      document_title: 'Software Engineer Offer',
      risk_score: 90,
      risk_level: 'HIGH RISK',
      confidence: 95,
      severity_color: '#EF4444',
      severity_bg: 'rgba(239, 68, 68, 0.1)',
      claimed_company: 'Global Systems',
      analyzed_at: new Date().toISOString(),
      primary_indicators: ['Advance Fee', 'Urgency Pressure'],
      expires_in_hours: 24,
      expires_in_minutes: 30,
      alert_title: 'New Login Detected',
      alert_description: 'An authenticated sign-in occurred from a new device.',
      event_type: 'LOGIN_SUCCESS',
      timestamp: new Date().toISOString(),
      ip_address: '127.0.0.1',
      browser: 'Chrome 128',
      os: 'Windows 11',
      shared_by: 'Analyst Sarah',
      share_token: 'SG-928471',
      deleted_at: new Date().toISOString()
    });
    if (!html || html.length < 100) {
      throw new Error(`Template ${t} rendered empty or too small.`);
    }
    console.log(`[PASS] Template '${t}' rendered cleanly (${html.length} bytes).`);
  }

  console.log('\nTesting sendEmail dispatch...');
  const res = await sendEmail({
    to: 'test@example.com',
    template: 'welcome',
    data: { username: 'AnalystOne', login_url: 'http://localhost:5000/login.html' }
  });
  console.log('[PASS] Dispatch test result:', res);
  console.log('\nAll Mailer unit tests completed successfully!');
}

runTest().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
