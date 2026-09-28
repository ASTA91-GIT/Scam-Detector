# AI-Powered Job & Internship Scam Detector

A full-stack cybersecurity application that uses a **Local Offline Large Language Model (LLM)** and an intelligent multi-pass OCR extraction pipeline to detect fraudulent job offers and internship scams. Built with Flask (Python), MongoDB, Ollama, and vanilla JavaScript with rich 3D animations.

---

## 🎯 Architecture & Primary Intelligence Flow

The system runs entirely **locally and offline** without requiring any external cloud AI API keys (no OpenAI, Gemini, Groq, or Hugging Face required during inference).

```
USER UPLOAD (PDF, PNG, JPG, WEBP, or Text)
    ↓
FILE VALIDATION & SECURITY SANITIZATION
    ↓
OCR / PDF EXTRACTION (pypdf + pypdfium2 + Tesseract)
    ↓
TEXT CLEANING & PRESERVATION OF STRUCTURE
    ↓
LOCAL OFFLINE LLM (Ollama: llama3.2:3b / llama3.1:8b)
    ↓
SEMANTIC & CONTEXTUAL FORENSIC ANALYSIS
    ↓
CALIBRATED RISK SCORE (0–100) + CONFIDENCE (0–100)
    ↓
EVIDENCE-LINKED REASONING WITH EXACT QUOTES
    ↓
RESULT PAGE & CASEAI INVESTIGATION ASSISTANT
```

---

## ✨ Key Features

### 1. Local Offline AI (No Cloud API Keys)
- **Primary Engine**: Uses **Ollama** running locally on `http://localhost:11434`.
- **Supported Models**: `llama3.2:3b` (fast, GPU/CPU-friendly) or `llama3.1:8b`.
- **100% Offline & Private**: Candidate resumes, job offers, and sensitive personal information never leave the machine.
- **Fail-Safe Integrity**: If Ollama or the configured model is unavailable, the backend clearly reports:
  > *"Local AI model unavailable. Start Ollama and ensure the configured model is installed."*
  Never produces fake AI results or silently falls back to third-party cloud services.

### 2. Semantic Forensic Analysis (Beyond Keyword Matching)
- Decides risk based on **meaning, intent, and social engineering behaviors**, not hardcoded keyword counts.
- Detects:
  - Upfront advance payments, registration fees, and equipment deposits.
  - Cashier check overpayment and money mule schemes.
  - Artificial urgency, deadline pressure, and coercion.
  - Mismatched recruiter domains (e.g., claiming Microsoft but using a free Gmail address).
  - Out-of-band communication redirection (demanding Telegram/WhatsApp contact).
  - Premature credential and identity harvesting (SSN, ID scans, banking logins).

### 3. Separation of AI-Generated Content from Scams
- Perfectly formatted AI-written documents are **NOT** automatically classified as scams.
- The detector evaluates whether the *content and contractual terms* contain suspicious characteristics.
- Includes a dedicated `document_assessment` check distinguishing potential synthetic document formatting from fraudulent behavior.

### 4. Advanced OCR & PDF Text Extraction
- **Supported Formats**: PDF (text-based and scanned), PNG, JPG, JPEG, and WEBP.
- **Multi-Pass OCR**: Uses adaptive thresholding and grayscale pre-processing.
- **Pure Python PDF Rendering**: Uses `pypdfium2` for scanned PDF page rendering without requiring external Windows Poppler binaries.
- **Transparency on Extraction Quality**: Warns users if image blur or low resolution degrades extraction confidence.

### 5. Evidence-Linked Reasoning ("Why Did I Get This Score?")
- Every risk factor includes:
  - **Finding**: Summary of the suspicious tactic.
  - **Severity**: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
  - **Evidence**: Direct, verbatim quoted text from the uploaded document.
  - **Explanation**: Actionable breakdown of the risk.
  - **Score Impact**: Points contributed to the overall 0–100 score.

### 6. Interactive CaseAI Assistant
- Full conversational AI assistant tied directly to each analyzed case.
- Explains findings, drafts inquiry emails to official company HR departments, generates evidence verification checklists, and streams real-time SSE responses.

---

## 📁 Project Structure

```
scam-detector/
├── app.py                       # Main Flask entrypoint & API router
├── seed_test_user.py            # Idempotent development test account seeder
├── requirements.txt             # Python dependencies
├── .env                         # Environment configuration
├── backend/
│   ├── ai/
│   │   ├── provider.py          # AI Provider abstract base class
│   │   ├── ollama_provider.py   # Ollama local offline inference client
│   │   ├── provider_factory.py  # Provider factory & status health checks
│   │   ├── prompts.py           # Forensic analyst prompts & injection defense
│   │   └── case_context.py      # CaseAI context linkage
│   ├── ai_analyzer.py           # Analysis routing abstraction
│   ├── analysis.py              # Primary scam analysis orchestration
│   ├── auth.py                  # JWT authentication routes
│   ├── auth_utils.py            # Password hashing & JWT helpers
│   ├── case_ai.py               # CaseAI interactive chat service
│   ├── case_ai_routes.py        # CaseAI HTTP & SSE streaming endpoints
│   ├── database.py              # MongoDB connection & collections
│   ├── file_utils.py            # File validation, sanitization & extraction
│   └── ocr_utils.py             # Multi-pass OCR & pypdfium2 PDF pipeline
├── frontend/
│   ├── index.html               # 3D Spider-Man themed landing page
│   ├── analyze.html             # Multi-format upload & text analysis UI
│   ├── analyze.js               # 7-stage animated analysis pipeline controller
│   ├── result.html              # Forensic report, evidence cards & CaseAI UI
│   ├── result.js                # Evidence cards & CaseAI chat controller
│   ├── dashboard.html           # Case history & statistics
│   ├── login.html / signup.html # Authentication pages
│   └── styles.css               # Core styling & glassmorphic themes
└── tests/
    ├── test_scam_detection_suite.py # Complete 10-test automated verification suite
    └── data/                        # OCR & blur test artifacts
```

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.12 / 3.14)
- MongoDB running locally (`mongodb://127.0.0.1:27017/`)
- [Ollama](https://ollama.com) installed and running locally
- Tesseract OCR (optional, for image OCR)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Ollama & Local Model
1. Start the Ollama background service:
   ```bash
   ollama serve
   ```
2. Pull the preferred local model:
   ```bash
   ollama pull llama3.2:3b
   ```
   *(Or for 8B models on higher-spec machines: `ollama pull llama3.1:8b`)*

### Step 3: Configure Environment (`.env`)
Create or edit `.env` in the project root:
```env
MONGO_URI=mongodb://127.0.0.1:27017/job_scam_detector
PORT=5000
SECRET_KEY=dev-secret-key-change-in-production
FLASK_ENV=development
FLASK_DEBUG=True

# File Upload Configuration
MAX_FILE_SIZE=10485760
UPLOAD_FOLDER=uploads
ALLOWED_EXTENSIONS=pdf,doc,docx,txt,png,jpg,jpeg,webp

# Local Offline AI Configuration (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
AI_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=120
```

### Step 4: Seed the Dedicated Development Test User
Create or reset the idempotent test account:
```bash
python seed_test_user.py
```
**Test Credentials:**
- **Email**: `test@scamdetector.local`
- **Password**: `Test@12345`
- **Role**: Test User with full access to login, upload, reports, and CaseAI.

### Step 5: Start the Backend Server
```bash
python app.py
```
The server will start on `http://127.0.0.1:5000`.

---

## 🧪 Automated Testing

### 1. End-to-End Forensic Analysis Suite
Runs all 10 forensic test scenarios (A through J) with real local GPU/CPU inference, verifying extraction, score clamping, evidence quotes, MongoDB persistence, and CaseAI context:
```bash
python tests/test_scam_detection_suite.py
```

**Test Coverage:**
- **A. Legitimate Offer**: Low risk (0/100), full salary/benefits, 0 scam deductions.
- **B. Traditional Scam**: High risk (100/100), task VIP deposit, Telegram contact.
- **C. AI-Generated Professional Scam**: High risk (85/100), polished language with hidden ₹4,999 deposit.
- **D. Blurry Document**: Low confidence warning with graceful handling.
- **E. OCR-Heavy Document**: Image-based scanned offer processed via Tesseract OCR.
- **F. Financial Scam**: Fake cashier check overpayment and refund fraud.
- **G. Credential Harvesting Scam**: Premature demands for SSN, driver's license, and bank login.
- **H. Suspicious Recruiter Identity**: Microsoft imposter using a `@gmail.com` address.
- **I. Long Document**: Multi-page Master Employment Agreement contextual analysis.
- **J. Prompt Injection Defense**: Evaluates resistance against adversarial prompt override directives.

### 2. CaseAI HTTP & SSE Streaming Test
Verifies CaseAI live chat, Server-Sent Events (SSE) streaming, checklist generation, and conversation history:
```bash
python -m backend.test_case_ai_http
```

---

## 📡 API Reference

### Health & Diagnostics
- `GET /api/ai/status` — Returns local Ollama availability, active provider, base URL, and installed models.

### Authentication
- `POST /api/auth/signup` — Register new user
- `POST /api/auth/login` — Authenticate and receive JWT token
- `GET /api/auth/verify` — Validate session token

### Scam Analysis
- `POST /api/analysis/analyze` (or `POST /api/analyze`) — Multipart file upload or JSON payload analysis.
- `GET /api/analysis/result/<id>` — Retrieve full forensic report by case ID.

### CaseAI Interactive Assistant
- `GET /api/cases/<id>/chat/context` — Retrieve case-grounded forensic context.
- `POST /api/cases/<id>/chat` — Synchronous chat.
- `POST /api/cases/<id>/chat/stream` — Real-time Server-Sent Events (SSE) streaming response.
- `POST /api/cases/<id>/chat/action` — Trigger specialist actions (`generate_checklist`, `draft_inquiry_email`, etc.).
- `GET /api/cases/<id>/chat/export` — Export case conversation transcript.

---

## 🛡️ Security & Privacy
- **Untrusted Input Isolation**: All documents are treated as untrusted forensic evidence. Explicit prompt boundaries defend against prompt injection.
- **Path Traversal Protection**: Uploaded filenames are sanitized with UUID prefixes and secured against path traversal attacks.
- **Zero Cloud Leakage**: Inference occurs on `localhost` without transmitting documents to third-party AI APIs.
- **Owner-Scoped Data**: Case histories and CaseAI sessions are strictly scoped to the authenticated user ID.

---

## 📄 License
This project is open-source and intended for educational, research, and consumer protection purposes.
