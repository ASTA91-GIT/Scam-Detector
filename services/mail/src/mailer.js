/**
 * Reusable Nodemailer Transporter and Template Renderer
 * Supports generic SMTP relays with development fallback simulation.
 */

const nodemailer = require('nodemailer');
const fs = require('fs');
const path = require('path');

let transporter = null;
let isConfigured = false;
let isSimulator = false;

function initMailer() {
  const host = process.env.SMTP_HOST;
  const port = parseInt(process.env.SMTP_PORT || '587', 10);
  const secure = process.env.SMTP_SECURE === 'true' || port === 465;
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASSWORD;

  if (host && host !== 'smtp.example.com' && user && pass && pass !== 'your-smtp-password') {
    transporter = nodemailer.createTransport({
      host,
      port,
      secure,
      auth: { user, pass },
      tls: {
        rejectUnauthorized: process.env.NODE_ENV === 'production'
      }
    });
    isConfigured = true;
    isSimulator = false;
    console.log(`[MAIL] Configured generic SMTP transport -> ${host}:${port} (secure=${secure})`);
  } else {
    // Simulator / Local development mode
    transporter = {
      sendMail: async (mailOptions) => {
        console.log(`\n======================================================`);
        console.log(`[MAIL SIMULATOR] Dispatching Email to: ${mailOptions.to}`);
        console.log(`Subject: ${mailOptions.subject}`);
        console.log(`From: ${mailOptions.from}`);
        console.log(`======================================================\n`);
        return { messageId: `sim-${Date.now()}`, simulated: true };
      },
      verify: async () => true
    };
    isConfigured = true;
    isSimulator = true;
    console.log('[MAIL] Operating in local development simulator mode (Safe dispatch logging).');
  }
}

/**
 * Basic template interpolation replacing {{key}} and simple helpers
 */
function renderTemplate(templateName, data = {}) {
  const filePath = path.join(__dirname, 'templates', `${templateName}.html`);
  if (!fs.existsSync(filePath)) {
    throw new Error(`Email template '${templateName}' not found.`);
  }

  let html = fs.readFileSync(filePath, 'utf8');

  // Handle simple array iteration: {{#each list}} <li>{{this}}</li> {{/each}}
  html = html.replace(/{{#each\s+([a-zA-Z0-9_]+)}}([\s\S]*?){{\/each}}/g, (match, arrayKey, inner) => {
    const arr = data[arrayKey];
    if (Array.isArray(arr) && arr.length > 0) {
      return arr.map(item => inner.replace(/{{this}}/g, String(item))).join('');
    }
    return '';
  });

  // Handle simple conditional: {{#if key}} ... {{/if}}
  html = html.replace(/{{#if\s+([a-zA-Z0-9_]+)}}([\s\S]*?){{\/if}}/g, (match, condKey, inner) => {
    const val = data[condKey];
    return (val && (!Array.isArray(val) || val.length > 0)) ? inner : '';
  });

  // Replace variable placeholders {{key}}
  html = html.replace(/{{([a-zA-Z0-9_]+)}}/g, (match, key) => {
    return data[key] !== undefined ? String(data[key]) : '';
  });

  return html;
}

/**
 * Dispatch an email
 */
async function sendEmail({ to, template, subject, data = {} }) {
  if (!transporter) {
    initMailer();
  }

  const fromName = process.env.SMTP_FROM_NAME || 'ScamGuard AI Forensics';
  const fromEmail = process.env.SMTP_FROM || 'security@scamguard.ai';
  const from = `"${fromName}" <${fromEmail}>`;

  const html = renderTemplate(template, data);

  const defaultSubjects = {
    'welcome': 'Welcome to ScamGuard AI Forensic Platform',
    'verify-email': 'Verify Your Email Address - ScamGuard AI',
    'password-reset': 'Password Reset Request - ScamGuard AI',
    'security-alert': `Security Alert: ${data.alert_title || 'Account Activity'}`,
    'analysis-complete': `Forensic Threat Report Complete [${data.risk_level || 'ANALYSIS'}] - Case #${data.case_id || 'SG'}`,
    'report-share': `Forensic Dossier Shared With You - ${data.document_title || 'Document'}`,
    'account-deleted': 'Account Deletion Confirmation - ScamGuard AI'
  };

  const mailOptions = {
    from,
    to,
    subject: subject || defaultSubjects[template] || 'ScamGuard AI Notification',
    html
  };

  const info = await transporter.sendMail(mailOptions);
  return {
    success: true,
    messageId: info.messageId,
    simulated: !!info.simulated
  };
}

module.exports = {
  initMailer,
  sendEmail,
  renderTemplate,
  isConfigured: () => isConfigured,
  isSimulator: () => isSimulator
};
