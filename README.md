# ScamGuard AI — Production-Ready Forensic Scam Intelligence Platform

ScamGuard AI is an enterprise-grade cybersecurity SaaS application that analyzes employment offers, recruitment correspondence, and onboarding documents to detect fraudulent scams, advance fee fraud, impersonation, and identity harvesting.

Built with a hardened Python/Flask core, local offline AI via Ollama, a dedicated Node.js Nodemailer microservice, and MongoDB.

---

## 🏗️ System Architecture

```
                          [ Client Browser ]
                                   │
              ┌────────────────────┴────────────────────┐
              │ HTTPS / Strict CSP / Security Headers   │
              ▼                                         ▼
   [ Flask API Backend (5000) ]             [ Frontend SPA ]
      - Auth & Token Revocation                - HTML5 / CSS3 / Vanilla JS
      - Multi-Stage Analysis Pipeline          - Forensic Investigation Console
      - SSRF & Safe Network Filters            - Real-time Stage Progression
      - File Upload Security Validation        - Security Center & Sessions
      - Rate Limiting & Audit Logging          - Standalone Forensic A4 PDF
              │                     │
              ▼                     ▼
     [ Local Ollama AI ]     [ MongoDB (27017) ]
      - llama3.2:3b           - Users & Sessions
      - 100% Offline          - Analyses & History
      - Zero Cloud Fallback   - Audit Logs & Indexes
              │
              ▼
   [ Node.js Mail Service (5001) ]
      - Express + Nodemailer
      - Generic SMTP / Dev Simulator
      - Protected by Internal Secret
```

---

## 🛡️ Enterprise Security Features

1. **Local Authoritative AI Analysis (Zero Cloud Fallback)**
   - All forensic analysis is executed locally and privately using Ollama (`llama3.2:3b`).
   - Resumes, offers, and extracted personal data never leave your infrastructure.
   - If Ollama is offline, the API reports a transparent 503 service unavailable response rather than faking results or leaking data to third-party cloud LLMs.

2. **File Upload Security & Magic Byte Validation**
   - Filename sanitization and internal UUID randomization preventing path traversal.
   - Deep signature verification (magic bytes) for PDF (`%PDF-`), PNG, JPEG, WEBP, and DOCX.
   - Executable rejection (`MZ`, `ELF`, shell scripts).
   - Decompression bomb guard via Pillow (`Image.MAX_IMAGE_PIXELS`).
   - Page count limit enforcement (`MAX_DOCUMENT_PAGES=20`).

3. **Server-Side Request Forgery (SSRF) Protection**
   - Blocks all requests to private networks, loopback addresses (`127.0.0.1`, `localhost`), link-local IPs, and cloud metadata endpoints (`169.254.169.254`).
   - Protocol restriction to `http://` and `https://` only.
   - DNS resolution pre-flight validation preventing DNS rebinding.

4. **Dedicated Node.js Nodemailer Microservice**
   - Clean Express service running on port 5001.
   - Protected with internal bearer secret (`MAIL_SERVICE_SECRET`).
   - Supports generic production SMTP alongside an automated local development simulator.
   - 7 responsive email templates: `welcome`, `verify-email`, `password-reset`, `security-alert`, `analysis-complete`, `report-share`, and `account-deleted`.

5. **Token Revocation & Active Session Management**
   - Active device sessions tracking (User-Agent parsing, IP metadata, last seen).
   - Immediate token invalidation via `token_version` incrementing upon password reset or remote logout.
   - "Sign Out Other Sessions" capabilities.

6. **Rate Limiting & Immutable Audit Logging**
   - Sliding-window in-memory rate limiting across sensitive endpoints (`/login`, `/register`, `/forgot-password`, `/analyze`).
   - Immutable audit logging in `audit_logs` collection for all key security events.

7. **Automatic File Retention Cleanup**
   - Automated pruning of temporary uploaded files exceeding retention policy (`FILE_RETENTION_HOURS=24`).

8. **Secure Report Sharing & Public Verification**
   - High-entropy cryptographic share tokens (`/shared/report/<token>`) with optional expiration and owner revocation.
   - Public report verification registry (`/verify/report/<public_id>`) proving analysis authenticity without exposing private documents.

---

## 📋 Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `FLASK_ENV` | Application environment (`development` or `production`) | `production` |
| `SECRET_KEY` | Flask cryptographic session key | Secure random string |
| `JWT_SECRET` | Secret key for signing authentication JWTs | Secure random string |
| `MONGODB_URI` | MongoDB connection URI | `mongodb://127.0.0.1:27017/job_scam_detector` |
| `OLLAMA_BASE_URL`| Local Ollama API host | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Authoritative forensic model | `llama3.2:3b` |
| `MAIL_SERVICE_URL` | Internal Node.js mail service endpoint | `http://localhost:5001` |
| `MAIL_SERVICE_SECRET` | Shared secret protecting the internal mail API | Secure random string |
| `SMTP_HOST` | Outbound mail SMTP host | `smtp.example.com` |
| `SMTP_PORT` | Outbound mail SMTP port | `587` |
| `SMTP_USER` | SMTP authentication username | `apikey` |
| `SMTP_PASSWORD` | SMTP authentication password | Secret |
| `SMTP_FROM` | Sender email address | `no-reply@scamguard.local` |
| `FRONTEND_URL` | Allowed origin for production CORS | `http://localhost:5000` |
| `MAX_UPLOAD_SIZE` | Maximum upload size in bytes | `10485760` (10MB) |
| `MAX_DOCUMENT_PAGES`| Maximum permitted pages in a PDF | `20` |
| `FILE_RETENTION_HOURS`| Temporary document cleanup interval | `24` |
| `RATE_LIMIT_ENABLED` | Global rate limiting toggle | `true` |
| `HIGH_RISK_EMAIL_THRESHOLD` | Score triggering high-risk email alerts | `75` |

---

## 🚀 Quickstart & Local Execution

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB 6.0+ (running locally on port 27017)
- Ollama with model `llama3.2:3b` (`ollama pull llama3.2:3b`)

### 1. Install Dependencies
```bash
# Python dependencies
pip install -r requirements.txt

# Mail microservice dependencies
cd services/mail
npm install
cd ../..
```

### 2. Start Services

**Terminal 1: Ollama Server**
```bash
ollama serve
```

**Terminal 2: Node.js Mail Microservice**
```bash
node services/mail/server.js
```

**Terminal 3: Flask Backend & Web Application**
```bash
python app.py
```

Open your browser at `http://localhost:5000`.

---

## 🐳 Docker Production Deployment

Run the complete multi-service stack (Flask API + Node Mail Service + MongoDB):

```bash
docker compose up -d --build
```

The stack exposes:
- ScamGuard Web & API: `http://localhost:5000`
- MongoDB: `localhost:27017`
- Mail Service (Internal): `http://localhost:5001`

---

## 🔍 Preflight Verification Script

Before deploying to production, execute the automated preflight checker:

```bash
python scripts/preflight_check.py
```

Output checks:
```
=================================================================
  SCAMGUARD AI — PRODUCTION PREFLIGHT CHECK
=================================================================
  [✓] Configuration & Environment Variables
  [✓] MongoDB Connection & Required Indexes
  [✓] Ollama Engine & Model (llama3.2:3b)
  [✓] OCR & Document Pipeline (pypdfium2: OK, PyPDF2: OK, Pillow: OK)
  [✓] Node.js Mail Service (Simulator / SMTP)
  [✓] Domain Intelligence & SSRF Protection Filters
  [✓] Upload Directory Storage Permissions
  [✓] Security Configuration (Debug disabled)
=================================================================
  RESULT: READY FOR DEPLOYMENT
=================================================================
```

---

## 🧪 Automated Testing

Execute the complete production test suite:

```bash
pytest tests/test_production_readiness_suite.py -v
```

Execute forensic and certificate tests:
```bash
python tests/test_forensic_console_suite.py
python tests/test_certificate_scam_suite.py
```

---

## 📡 API Reference Overview

- **Auth**: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/verify-email`, `POST /api/auth/resend-verification`, `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`, `GET /api/auth/sessions`, `POST /api/auth/sessions/revoke-others`, `PUT /api/auth/notification-preferences`
- **Analysis**: `POST /api/analyze`, `POST /api/analyze/job`, `GET /api/analyze/job/<id>`, `GET /api/analysis/result/<id>`
- **Reports**: `POST /api/saved-reports/<id>/share`, `GET /api/saved-reports/shared/<token>`, `GET /api/saved-reports/verify/<public_id>`
- **Admin**: `GET /api/admin/metrics`, `GET /api/admin/users`, `GET /api/admin/audit-logs`, `GET /api/admin/system-health`
- **Health**: `GET /api/health`, `GET /api/ready`, `GET /api/ai/status`
