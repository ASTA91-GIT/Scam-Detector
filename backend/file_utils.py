"""
File Upload and Text Extraction Utilities
Supports:
- PNG, JPG, JPEG, WEBP (Image OCR)
- Text-based PDFs (PyPDF2 + pdfplumber)
- Scanned PDFs (pypdfium2 + Tesseract OCR)
- TXT, DOC, DOCX
"""

import os
import re
from typing import Tuple, Dict, Any, Optional
import PyPDF2
import pdfplumber
from docx import Document
from werkzeug.utils import secure_filename
from flask import current_app

from backend.ocr_utils import (
    extract_text_from_image,
    extract_text_from_pdf_ocr,
    clean_extracted_text,
    assess_extraction_quality
)

# -----------------------------
# CONFIGURATION
# -----------------------------

ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt',
    'png', 'jpg', 'jpeg', 'webp'
}

# -----------------------------
# FILE TYPE VALIDATION
# -----------------------------

def allowed_file(filename: str) -> bool:
    """Validate allowed file extension safely"""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# -----------------------------
# EXTRACTION HELPERS
# -----------------------------

def extract_text_from_pdf_native(file_path: str) -> str:
    """Extract text from text-based PDF using PyPDF2 & pdfplumber"""
    text = ""
    # Try PyPDF2 first
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"PyPDF2 error: {e}")

    # If PyPDF2 got very little text, try pdfplumber
    if len(text.strip()) < 50:
        try:
            with pdfplumber.open(file_path) as pdf:
                plumber_text = ""
                for page in pdf.pages:
                    pt = page.extract_text()
                    if pt:
                        plumber_text += pt + "\n"
                if len(plumber_text.strip()) > len(text.strip()):
                    text = plumber_text
        except Exception as e:
            print(f"pdfplumber error: {e}")

    return clean_extracted_text(text)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX"""
    try:
        doc = Document(file_path)
        full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return clean_extracted_text(full_text)
    except Exception as e:
        print(f"DOCX extraction error: {e}")
        return ""


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT with encoding fallback"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return clean_extracted_text(f.read())
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
            return clean_extracted_text(f.read())


# -----------------------------
# MASTER EXTRACTION PIPELINE
# -----------------------------

def extract_text_from_file(file_path: str, file_extension: str) -> Dict[str, Any]:
    """
    Master extractor according to specification:
    FILE
     ↓
    validate MIME/type/size
     ↓
    extract native PDF text if available
     ↓
    otherwise OCR
     ↓
    clean OCR artifacts
     ↓
    preserve useful formatting
     ↓
    return complete text + quality metadata
    """
    ext = file_extension.lower().lstrip('.')

    if ext == 'txt':
        text = extract_text_from_txt(file_path)
        quality = assess_extraction_quality(text)
        return {
            "text": text,
            "method": "text_file",
            "quality_warning": quality["warning"],
            "is_poor": quality["is_poor"],
            "word_count": quality["word_count"]
        }

    if ext in ['doc', 'docx']:
        text = extract_text_from_docx(file_path)
        quality = assess_extraction_quality(text)
        return {
            "text": text,
            "method": "docx_file",
            "quality_warning": quality["warning"],
            "is_poor": quality["is_poor"],
            "word_count": quality["word_count"]
        }

    if ext in ['png', 'jpg', 'jpeg', 'webp']:
        res = extract_text_from_image(file_path)
        return {
            "text": res["text"],
            "method": "image_ocr",
            "quality_warning": res["quality_warning"],
            "is_poor": res["is_poor"],
            "word_count": res["word_count"]
        }

    if ext == 'pdf':
        # Step 1: Attempt native text extraction
        native_text = extract_text_from_pdf_native(file_path)
        if len(native_text.strip()) >= 50:
            quality = assess_extraction_quality(native_text)
            return {
                "text": native_text,
                "method": "native_pdf",
                "quality_warning": quality["warning"],
                "is_poor": quality["is_poor"],
                "word_count": quality["word_count"]
            }

        # Step 2: Fall back to scanned PDF OCR via pypdfium2
        ocr_res = extract_text_from_pdf_ocr(file_path)
        return {
            "text": ocr_res["text"],
            "method": "scanned_pdf_ocr",
            "quality_warning": ocr_res["quality_warning"],
            "is_poor": ocr_res["is_poor"],
            "word_count": ocr_res["word_count"]
        }

    raise ValueError(f"Unsupported file type: {ext}")


# -----------------------------
# SAFE FILE STORAGE
# -----------------------------

def save_uploaded_file(file, user_id: str) -> Tuple[str, str]:
    """
    Saves uploaded file securely:
    - Verifies extension
    - Sanitizes filename to prevent path traversal
    - Prefixes with user_id to ensure user isolation
    """
    if not allowed_file(file.filename):
        raise ValueError("File type not allowed. Supported formats: PDF, PNG, JPG, JPEG, WEBP, DOC, DOCX, TXT")

    # Sanitize original filename
    base_name = secure_filename(os.path.basename(file.filename))
    if not base_name:
        base_name = "upload_document"

    safe_filename = f"{user_id}_{base_name}"

    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, safe_filename)
    # Ensure resolved path is strictly within upload directory (prevent traversal)
    if not os.path.abspath(file_path).startswith(os.path.abspath(upload_dir)):
        raise PermissionError("Path traversal attempt detected.")

    file.save(file_path)
    return file_path, safe_filename