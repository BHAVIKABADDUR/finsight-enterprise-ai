import os
import pytesseract
from pathlib import Path
from loguru import logger

IS_CLOUD = os.getenv("HOME", "").startswith("/home/adminuser")

if not IS_CLOUD:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_from_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError("PDF not found: " + str(pdf_path))

    if IS_CLOUD:
        # Use pdfplumber on cloud - no poppler needed
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                text = "".join(page.extract_text() or "" for page in pdf.pages)
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")
        # Fallback: try poppler
        import subprocess
        result = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        return "PDF text could not be extracted"
    else:
        # Local - use pdf2image + OCR
        from pdf2image import convert_from_path
        POPPLER_PATH = r"C:\Program Files\poppler-26.02.0\Library\bin"
        pages = convert_from_path(str(pdf_path), dpi=300, poppler_path=POPPLER_PATH)
        full_text = []
        for i, page in enumerate(pages):
            text = pytesseract.image_to_string(page, config="--psm 6")
            full_text.append("Page " + str(i+1) + ": " + text)
        sep = chr(10) + chr(10)
        return sep.join(full_text)


def extract_text_from_directory(directory):
    directory = Path(directory)
    results = {}
    for pdf_path in directory.glob("*.pdf"):
        try:
            results[pdf_path.name] = extract_text_from_pdf(str(pdf_path))
        except Exception as e:
            results[pdf_path.name] = ""
    return results

# v2
