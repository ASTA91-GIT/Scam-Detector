"""
Generate Test Assets for Scam Detection Test Suite
Generates test documents, images (blurry, OCR-heavy, WEBP), and files for automated testing.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(TEST_DATA_DIR, exist_ok=True)

def generate_blurry_image():
    """Generates an intentionally blurry document to trigger low extraction confidence"""
    img = Image.new('RGB', (700, 300), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    text = "Faint Offer Notice: Contact admin for payment verification."
    draw.text((30, 100), text, fill=(160, 160, 160))

    # Apply heavy blur to simulate bad scan / out-of-focus camera capture
    blurred = img.filter(ImageFilter.GaussianBlur(radius=6))
    out_path = os.path.join(TEST_DATA_DIR, "blurry_document.png")
    blurred.save(out_path)
    print(f"[OK] Generated: {out_path}")
    return out_path

def generate_ocr_image():
    """Generates a sharp image with clear text for OCR testing (PNG and WEBP)"""
    img = Image.new('RGB', (900, 450), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    lines = [
        "GLOBAL TECH SOLUTIONS - APPOINTMENT LETTER",
        "Role: Junior Support Associate",
        "Base Salary: $45,000 per annum",
        "Notice: Prior to onboarding equipment dispatch, employee must pay",
        "a refundable equipment insurance deposit of $150 via Zelle.",
        "Reply immediately to hr-verification@tech-solution-portal.biz"
    ]

    y = 40
    for line in lines:
        draw.text((40, y), line, fill=(10, 10, 10))
        y += 55

    png_path = os.path.join(TEST_DATA_DIR, "ocr_sample.png")
    img.save(png_path)
    print(f"[OK] Generated: {png_path}")

    # Also save as WEBP to verify WEBP OCR support
    webp_path = os.path.join(TEST_DATA_DIR, "ocr_sample.webp")
    img.save(webp_path, "WEBP")
    print(f"[OK] Generated: {webp_path}")

    return png_path, webp_path

if __name__ == "__main__":
    generate_blurry_image()
    generate_ocr_image()
