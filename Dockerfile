# ScamGuard AI - Production Dockerfile
FROM python:3.11-slim

# System dependencies for OCR, PDF rendering, and crypto
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy application source
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY app.py gunicorn.conf.py seed_test_user.py ./

# Create runtime directories with appropriate permissions
RUN mkdir -p uploads/temporary uploads/avatars logs && \
    useradd -m -u 1000 scamguard && \
    chown -R scamguard:scamguard /app

USER scamguard

ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=5000

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/ready || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
