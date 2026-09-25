"""
File Upload and Text Extraction Utilities
Supports:
- TXT, DOC, DOCX
- Text-based PDFs
- Scanned PDFs (OCR)
- Image files (PNG, JPG, JPEG)
"""

import os
import PyPDF2
import pdfplumber
from docx import Document
from werkzeug.utils import secure_filename
from flask import current_app

from pdf2image import convert_from_path
from backend.ocr_utils import extract_text_from_image

# -----------------------------
# CONFIG
# -----------------------------

ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt',
    'png', 'jpg', 'jpeg'
}

# ⚠️ REQUIRED FOR WINDOWS (POPPLER)

POPPLER_PATH = r"D:\poppler\Library\bin" # 🔴 CHANGE if different

# -----------------------------
# FILE TYPE CHECK
# -----------------------------

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# -----------------------------
# TEXT EXTRACTION HELPERS
# -----------------------------

def extract_text_from_pdf(file_path):
    """Extract text from text-based PDF using PyPDF2"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception:
        return ""

def extract_text_from_pdf_plumber(file_path):
    """Extract text using pdfplumber (better layout support)"""
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception:
        return ""

def extract_text_from_docx(file_path):
    """Extract text from DOC/DOCX"""
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs).strip()

def extract_text_from_txt(file_path):
    """Extract text from TXT"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read().strip()

# -----------------------------
# MAIN EXTRACTION LOGIC
# -----------------------------

def extract_text_from_file(file_path, file_extension):
    """
    Master extractor:
    - Uses normal parsing first
    - Falls back to OCR if needed
    """
    ext = file_extension.lower()

    # ---------- TXT ----------
    if ext == 'txt':
        return extract_text_from_txt(file_path)

    # ---------- DOC / DOCX ----------
    if ext in ['doc', 'docx']:
        return extract_text_from_docx(file_path)

    # ---------- IMAGE OCR ----------
    if ext in ['png', 'jpg', 'jpeg']:
        return extract_text_from_image(file_path)

    # ---------- PDF ----------
    if ext == 'pdf':
        # 1️⃣ PyPDF2
        text = extract_text_from_pdf(file_path)

        # 2️⃣ pdfplumber
        if len(text.strip()) < 50:
            text = extract_text_from_pdf_plumber(file_path)

        # 3️⃣ If still weak → OCR
        if len(text.strip()) >= 50:
            return text.strip()

        # 4️⃣ OCR fallback (scanned PDF)
        images = convert_from_path(
            file_path,
            poppler_path=POPPLER_PATH
        )

        ocr_text = ""
        for idx, image in enumerate(images):
            temp_image = f"{file_path}_page_{idx}.png"
            image.save(temp_image, "PNG")

            ocr_text += extract_text_from_image(temp_image) + "\n"
            os.remove(temp_image)

        return ocr_text.strip()

    raise Exception(f"Unsupported file type: {ext}")

# -----------------------------
# FILE SAVE
# -----------------------------

def save_uploaded_file(file, user_id):
    """Save uploaded file safely and return path"""
    if not allowed_file(file.filename):
        raise Exception("File type not allowed")

    filename = secure_filename(file.filename)
    filename = f"{user_id}_{filename}"

    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    return file_path, filename
# -----------------------------