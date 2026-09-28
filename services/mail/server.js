/**
 * ScamGuard AI Mail Service Server
 * Secure internal microservice for transactional and security emails.
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../../.env') });
const express = require('express');
const { initMailer, sendEmail, isSimulator } = require('./src/mailer');

const app = express();
app.use(express.json({ limit: '1mb' }));

const PORT = parseInt(process.env.MAIL_PORT || '5001', 10);
const MAIL_SECRET = process.env.MAIL_SERVICE_SECRET || 'dev-internal-mail-secret';

// Initialize mailer
initMailer();

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'mail',
    simulator: isSimulator(),
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  });
});

// Internal email dispatch endpoint
app.post('/internal/send-email', async (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        error: { code: 'UNAUTHORIZED', message: 'Missing internal authorization token.' }
      });
    }

    const token = authHeader.split(' ')[1];
    if (token !== MAIL_SECRET) {
      return res.status(401).json({
        error: { code: 'FORBIDDEN', message: 'Invalid internal service token.' }
      });
    }

    const { to, template, subject, data } = req.body;
    if (!to || !template) {
      return res.status(400).json({
        error: { code: 'INVALID_PAYLOAD', message: "Fields 'to' and 'template' are required." }
      });
    }

    const result = await sendEmail({ to, template, subject, data });
    return res.status(200).json({
      success: true,
      messageId: result.messageId,
      simulated: result.simulated
    });
  } catch (err) {
    console.error('[MAIL ERROR]', err.message);
    return res.status(500).json({
      error: { code: 'SEND_FAILED', message: err.message }
    });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[MAIL SERVICE] ScamGuard AI Mail Service listening on port ${PORT}`);
});
