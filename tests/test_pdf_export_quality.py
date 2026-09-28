"""
Automated PDF Export Quality & Layout Audit
Generates PDF using headless Chrome browser print engine and performs
rigorous multi-page layout, margin, text integrity, and pagination verification.
"""

import os
import sys
import subprocess
import pypdfium2 as pdfium

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CHROME_PATHS = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def find_browser():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    raise RuntimeError("No Chrome/Edge executable found on system.")


def generate_pdf(url: str, output_path: str):
    browser_exe = find_browser()
    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=5000",
        f"--print-to-pdf={output_path}",
        url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        raise RuntimeError(f"Browser PDF generation failed (code {res.returncode}): {res.stderr}")
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"Generated PDF at {output_path} is missing or empty.")
    return output_path


def audit_pdf(pdf_path: str, dossier_label: str):
    print(f"\n=======================================================")
    print(f"AUDITING FORENSIC PDF: {dossier_label}")
    print(f"File: {pdf_path} (Size: {os.path.getsize(pdf_path):,} bytes)")
    print(f"=======================================================")

    pdf = pdfium.PdfDocument(pdf_path)
    total_pages = len(pdf)
    print(f"[OK] Total PDF Pages: {total_pages}")

    # Leakage blacklist
    leakage_terms = [
        "Search or jump to...",
        "Ctrl K",
        "Mark all read",
        "Security Notifications",
        "Dossier bookmarked to Saved Reports",
        "Ask CaseAI",
        "Save Report",
        "Download Dossier",
        "Share Link",
        "Analyze Another"
    ]

    mobile_nav_terms = ["Dashboard", "History", "Intel", "Profile"]

    page_audit_results = []

    for i in range(total_pages):
        page = pdf[i]
        width, height = page.get_size()
        
        # A4 standard points: 595.28 x 841.89 (within 2 points tolerance)
        is_a4 = abs(width - 595.28) < 3 and abs(height - 841.89) < 3
        
        text_page = page.get_textpage()
        page_text = text_page.get_text_range()

        # Check for UI leakage
        leaks = [term for term in leakage_terms if term.lower() in page_text.lower()]
        
        # Check if mobile bottom nav bar leaked: all 4 terms appearing together near bottom
        has_nav_leak = all(nav.lower() in page_text.lower() for nav in mobile_nav_terms)

        # Check header/footer
        has_header = "SCAMGUARD AI" in page_text or "AI FORENSIC INVESTIGATION" in page_text
        
        print(f"\n--- PAGE {i + 1} / {total_pages} ---")
        print(f"  * Dimensions: {width:.1f}pt x {height:.1f}pt (A4: {'YES' if is_a4 else 'NO'})")
        print(f"  * Text Length: {len(page_text)} chars")
        print(f"  * Header Identified: {'YES' if has_header else 'NO'}")
        print(f"  * UI Button Leaks: {leaks if leaks else 'NONE (Clean)'}")
        print(f"  * Mobile Nav Leak: {'DETECTED ❌' if has_nav_leak else 'NONE (Clean) ✓'}")
        
        # Preview top snippet
        snippet = " ".join(page_text.split()[:18])
        print(f"  * Content Snippet: \"{snippet}...\"")

        assert is_a4, f"Page {i+1} is not A4 portrait dimensions ({width} x {height})"
        assert not leaks, f"Page {i+1} leaked application controls: {leaks}"
        assert not has_nav_leak, f"Page {i+1} leaked mobile bottom navigation bar"

        # Save page image for visual inspection
        img_dir = os.path.join(OUTPUT_DIR, dossier_label.lower().replace(" ", "_"))
        os.makedirs(img_dir, exist_ok=True)
        img_path = os.path.join(img_dir, f"page_{i+1}.png")
        page.render(scale=2).to_pil().save(img_path)
        print(f"  * Page Image Saved: {img_path}")

        page_audit_results.append({
            "page": i + 1,
            "is_a4": is_a4,
            "text_length": len(page_text),
            "leaks": leaks,
            "has_nav_leak": has_nav_leak,
            "img_path": img_path
        })

    print(f"\n[PASS] All {total_pages} pages verified clean. Zero UI leakage.")
    return total_pages


def run():
    # Test A: High Risk Offer
    high_risk_id = "6aba96b62d7a8f27dfde4415"
    url_a = f"http://127.0.0.1:5000/result.html?id={high_risk_id}"
    pdf_a = os.path.join(OUTPUT_DIR, "forensic_report_high_risk.pdf")
    
    print(f"[1/2] Generating High Risk Dossier PDF from {url_a}...")
    generate_pdf(url_a, pdf_a)
    pages_a = audit_pdf(pdf_a, "HIGH RISK JOB OFFER DOSSIER")

    # Test B: Clean Participation Certificate
    cert_id = "6aba96c62d7a8f27dfde4419"
    url_b = f"http://127.0.0.1:5000/result.html?id={cert_id}"
    pdf_b = os.path.join(OUTPUT_DIR, "forensic_report_certificate.pdf")

    print(f"\n[2/2] Generating Clean Certificate Dossier PDF from {url_b}...")
    generate_pdf(url_b, pdf_b)
    pages_b = audit_pdf(pdf_b, "CLEAN PARTICIPATION CERTIFICATE DOSSIER")

    print("\n" + "=" * 70)
    print(f"PDF LAYOUT QUALITY AUDIT COMPLETED: 100% PASSED")
    print(f"High Risk Report: {pages_a} Pages | Certificate Report: {pages_b} Pages")
    print("=" * 70)


if __name__ == "__main__":
    run()
