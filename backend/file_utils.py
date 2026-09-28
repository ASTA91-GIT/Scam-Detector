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

import uuid
from PIL import Image

# -----------------------------
# CONFIGURATION
# -----------------------------

ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt',
    'png', 'jpg', 'jpeg', 'webp'
}

MAX_DOCUMENT_PAGES = int(os.getenv('MAX_DOCUMENT_PAGES', '20'))
MAX_IMAGE_DIMENSION = 10000  # pixels
MAX_IMAGE_PIXELS = 25000000  # decompression bomb guard

# File magic bytes signatures
FILE_SIGNATURES = {
    'pdf': [b'%PDF-'],
    'png': [b'\x89PNG\r\n\x1a\n'],
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'webp': [b'RIFF'],
    'docx': [b'PK\x03\x04'],
}

# -----------------------------
# FILE TYPE VALIDATION & SECURITY
# -----------------------------

def allowed_file(filename: str) -> bool:
    """Validate allowed file extension safely"""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_file_security(file_storage) -> Tuple[bool, str, str]:
    """
    Validates file upload strictly:
    - Verifies extension
    - Validates file signatures / magic bytes
    - Prevents executable uploads (MZ, ELF, etc.)
    - Validates PDF page count limit
    - Validates image dimensions and decompression bomb protection
    Returns:
        (is_valid: bool, file_ext: str, error_msg: str)
    """
    filename = file_storage.filename or ""
    if not allowed_file(filename):
        return False, "", "File type not permitted. Allowed: PDF, PNG, JPG, JPEG, WEBP, DOC, DOCX, TXT."

    ext = filename.rsplit('.', 1)[1].lower()

    # Read initial bytes for magic signature inspection
    stream = file_storage.stream
    stream.seek(0)
    header = stream.read(2048)
    stream.seek(0)

    # Immediately reject executables
    if header.startswith(b'MZ') or header.startswith(b'\x7fELF') or header.startswith(b'#!'):
        return False, ext, "Malicious file signature detected. Executable files are strictly prohibited."

    # Validate known signatures
    if ext in FILE_SIGNATURES:
        signatures = FILE_SIGNATURES[ext]
        matched = any(header.startswith(sig) for sig in signatures)
        if ext == 'webp' and matched:
            # WEBP has RIFF at 0 and WEBP at 8
            matched = len(header) >= 12 and header[8:12] == b'WEBP'

        if not matched:
            return False, ext, f"File content does not match the declared extension (.{ext}). Magic byte mismatch."

    # Specific deep inspection for PDFs
    if ext == 'pdf':
        try:
            reader = PyPDF2.PdfReader(stream)
            num_pages = len(reader.pages)
            stream.seek(0)
            if num_pages > MAX_DOCUMENT_PAGES:
                return False, ext, f"Document exceeds maximum permitted pages ({num_pages} > {MAX_DOCUMENT_PAGES})."
            if num_pages == 0:
                return False, ext, "Malformed or empty PDF document."
        except Exception as e:
            stream.seek(0)
            return False, ext, f"Corrupted or malformed PDF structure: {str(e)}"

    # Specific deep inspection for Images (Pillow decompression bomb protection & dimensions)
    if ext in ['png', 'jpg', 'jpeg', 'webp']:
        try:
            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
            with Image.open(stream) as img:
                img.verify()
            stream.seek(0)
            with Image.open(stream) as img:
                width, height = img.size
                if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    stream.seek(0)
                    return False, ext, f"Image dimensions too large ({width}x{height}, max {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION})."
            stream.seek(0)
        except Exception as img_err:
            stream.seek(0)
            return False, ext, f"Corrupted, invalid, or oversized image: {str(img_err)}"

    return True, ext, ""


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
    - Performs deep security validation (magic bytes, page limit, decompression bomb guard)
    - Sanitizes original filename for display
    - Generates random internal UUID filename to isolate filesystem and prevent path injection
    - Ensures file path cannot escape uploads directory
    """
    is_valid, ext, err_msg = validate_file_security(file)
    if not is_valid:
        raise ValueError(err_msg)

    # Sanitize original filename for display / metadata
    base_name = secure_filename(os.path.basename(file.filename or "upload_document"))
    if not base_name:
        base_name = f"document.{ext}"

    # Random internal storage filename (UUID-based)
    internal_filename = f"{uuid.uuid4().hex}_{str(user_id)[:8]}.{ext}"

    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, internal_filename)
    # Ensure resolved path is strictly within upload directory (prevent path traversal)
    abs_upload = os.path.abspath(upload_dir)
    abs_target = os.path.abspath(file_path)
    if not abs_target.startswith(abs_upload):
        raise PermissionError("Path traversal attempt detected.")

    file.save(file_path)
    return file_path, base_name