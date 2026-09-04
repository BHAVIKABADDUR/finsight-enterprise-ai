import os
import pytesseract
from pathlib import Path
from loguru import logger

# Detect cloud environment using multiple indicators
IS_CLOUD = (
    os.getenv("HOME", "").startswith("/home/adminuser") or
    os.path.exists("/mount/src") or
    os.getenv("STREAMLIT_SHARING_MODE") is not None or
    not os.path.exists(r"C:\Program Files\Tesseract-OCR")
)

if not IS_CLOUD:
    try:
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    except Exception:
        pass


def extract_text_from_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError("PDF not found: " + str(pdf_path))

    # Method 1: pdfplumber (pure Python, works everywhere)
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = " ".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            logger.info("Extracted text via pdfplumber")
            return text
    except Exception as e:
        logger.warning("pdfplumber failed: " + str(e))

    # Method 2: pdftotext command line (available on Linux/Streamlit Cloud)
    try:
        import subprocess
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info("Extracted text via pdftotext")
            return result.stdout
    except Exception as e:
        logger.warning("pdftotext failed: " + str(e))

    # Method 3: pdf2image + OCR (local Windows only)
    if not IS_CLOUD:
        try:
            from pdf2image import convert_from_path
            POPPLER_PATH = r"C:\Program Files\poppler-26.02.0\Library\bin"
            pages = convert_from_path(str(pdf_path), dpi=300, poppler_path=POPPLER_PATH)
            full_text = []
            for i, page in enumerate(pages):
                text = pytesseract.image_to_string(page, config="--psm 6")
                full_text.append("Page " + str(i+1) + ": " + text)
            sep = chr(10) + chr(10)
            return sep.join(full_text)
        except Exception as e:
            logger.warning("OCR failed: " + str(e))

    return "Could not extract text from PDF"


def extract_text_from_directory(directory):
    directory = Path(directory)
    results = {}
    for pdf_path in directory.glob("*.pdf"):
        try:
            results[pdf_path.name] = extract_text_from_pdf(str(pdf_path))
        except Exception as e:
            results[pdf_path.name] = ""
    return results
