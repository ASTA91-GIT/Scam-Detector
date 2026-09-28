"""
OCR and Text Cleaning Utilities
Handles multi-format OCR (PNG, JPG, JPEG, WEBP, Scanned PDF),
image preprocessing, artifact cleanup, and extraction quality assessment.
"""

import os
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image
from typing import Dict, Any, Optional

# ===============================
# CONFIGURE TESSERACT PATHS
# ===============================

# Default path for Windows installation
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"D:\SOFTWARES\tesseract.exe")
TESSDATA_PREFIX = os.getenv("TESSDATA_PREFIX", r"D:\SOFTWARES\tessdata")

if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

if os.path.exists(TESSDATA_PREFIX):
    os.environ["TESSDATA_PREFIX"] = TESSDATA_PREFIX


# ===============================
# TEXT CLEANING & NORMALIZATION
# ===============================

def clean_extracted_text(text: str) -> str:
    """
    Cleans OCR artifacts while preserving document structure and line breaks.
    - Normalizes Unicode spaces and quotes
    - Strips control characters
    - Fixes broken line continuations
    - Normalizes repeated empty lines
    """
    if not text:
        return ""

    # Replace common typographic Unicode with standard equivalents
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2013', '-').replace('\u2014', '--')
    text = text.replace('\u00a0', ' ')
    text = text.replace('\t', '    ')

    # Remove non-printable control characters except \n and \r
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Normalize carriage returns
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Fix spaces around linebreaks
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]

    # Collapse 3+ consecutive empty lines into 2
    cleaned_lines = []
    empty_count = 0
    for line in lines:
        if not line:
            empty_count += 1
            if empty_count <= 2:
                cleaned_lines.append("")
        else:
            empty_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def assess_extraction_quality(text: str) -> Dict[str, Any]:
    """
    Evaluates extraction text quality.
    If OCR produced garbled, incomplete, or low-density text,
    flags the warning required by specification:
    'Analysis confidence may be reduced because the extracted document text is incomplete or unclear.'
    """
    cleaned = clean_extracted_text(text)
    total_len = len(cleaned)

    if total_len == 0:
        return {
            "is_poor": True,
            "warning": "Analysis confidence may be reduced because the extracted document text is incomplete or unclear.",
            "char_count": 0,
            "word_count": 0,
            "alphanumeric_ratio": 0.0
        }

    words = re.findall(r'\b[a-zA-Z0-9]+\b', cleaned)
    word_count = len(words)
    alphanumeric_chars = sum(c.isalnum() for c in cleaned)
    alpha_ratio = alphanumeric_chars / max(total_len, 1)

    # Criteria for poor extraction:
    # 1. Very short (fewer than 30 characters)
    # 2. Fewer than 6 recognizable words
    # 3. Alphanumeric ratio < 45% (mostly gibberish/symbols)
    is_poor = (total_len < 30) or (word_count < 6) or (alpha_ratio < 0.45 and total_len > 40)

    warning_msg = None
    if is_poor:
        warning_msg = "Analysis confidence may be reduced because the extracted document text is incomplete or unclear."

    return {
        "is_poor": is_poor,
        "warning": warning_msg,
        "char_count": total_len,
        "word_count": word_count,
        "alphanumeric_ratio": round(alpha_ratio, 3)
    }


# ===============================
# IMAGE PREPROCESSING & OCR
# ===============================

def preprocess_image_for_ocr(image_bgr: np.ndarray) -> np.ndarray:
    """Preprocess image with grayscale and adaptive thresholding"""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2
    )
    return thresh


def extract_text_from_image(image_path_or_pil) -> Dict[str, Any]:
    """
    Extracts text from image file or PIL Image object.
    Supports PNG, JPG, JPEG, WEBP.
    Uses multi-pass approach (grayscale + adaptive threshold) to maximize accuracy.
    """
    try:
        if isinstance(image_path_or_pil, str):
            if not os.path.exists(image_path_or_pil):
                raise FileNotFoundError(f"Image file not found: {image_path_or_pil}")
            # Use PIL to read image first to support WEBP, PNG, JPG reliably
            pil_img = Image.open(image_path_or_pil)
        else:
            pil_img = image_path_or_pil

        # Convert PIL to OpenCV format
        rgb_img = pil_img.convert("RGB")
        bgr_img = cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2BGR)

        config = "--oem 3 --psm 6"

        # Pass 1: Grayscale with slight contrast adjustment
        gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        text_pass1 = pytesseract.image_to_string(gray, lang="eng", config=config).strip()

        # Pass 2: Adaptive Thresholding
        thresh = preprocess_image_for_ocr(bgr_img)
        text_pass2 = pytesseract.image_to_string(thresh, lang="eng", config=config).strip()

        # Choose the candidate with more coherent words
        words1 = len(re.findall(r'\b[a-zA-Z]{2,}\b', text_pass1))
        words2 = len(re.findall(r'\b[a-zA-Z]{2,}\b', text_pass2))

        chosen_text = text_pass1 if words1 >= words2 else text_pass2
        cleaned = clean_extracted_text(chosen_text)
        quality = assess_extraction_quality(cleaned)

        return {
            "text": cleaned,
            "quality_warning": quality["warning"],
            "is_poor": quality["is_poor"],
            "word_count": quality["word_count"],
            "char_count": quality["char_count"]
        }

    except Exception as e:
        print(f"❌ OCR Extraction error: {e}")
        return {
            "text": "",
            "quality_warning": "Analysis confidence may be reduced because the extracted document text is incomplete or unclear.",
            "is_poor": True,
            "word_count": 0,
            "char_count": 0,
            "error": str(e)
        }


# ===============================
# SCANNED PDF OCR WITH PYPDFIUM2
# ===============================

def extract_text_from_pdf_ocr(pdf_path: str, max_pages: int = 10) -> Dict[str, Any]:
    """
    Renders PDF pages to images and runs OCR on each page.
    Uses pypdfium2 natively (no poppler binary dependency needed on Windows).
    """
    combined_pages = []
    any_poor = False

    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        total_pages = min(len(pdf), max_pages)

        for i in range(total_pages):
            page = pdf[i]
            # Render at scale 2 for sharp OCR resolution (~144 dpi)
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()

            page_result = extract_text_from_image(pil_image)
            page_text = page_result.get("text", "").strip()
            if page_text:
                combined_pages.append(f"--- Page {i + 1} ---\n" + page_text)
            if page_result.get("is_poor"):
                any_poor = True

        full_text = "\n\n".join(combined_pages).strip()
        quality = assess_extraction_quality(full_text)

        return {
            "text": full_text,
            "quality_warning": quality["warning"] if (quality["is_poor"] or any_poor) else None,
            "is_poor": quality["is_poor"],
            "page_count": total_pages,
            "word_count": quality["word_count"]
        }

    except Exception as e:
        print(f"❌ PDF OCR error: {e}")
        return {
            "text": "",
            "quality_warning": "Analysis confidence may be reduced because the extracted document text is incomplete or unclear.",
            "is_poor": True,
            "page_count": 0,
            "word_count": 0,
            "error": str(e)
        }
