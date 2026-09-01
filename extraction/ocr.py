# extraction/ocr.py
# OCR layer -- converts PDF pages to text using Tesseract
# Handles both text-based and scanned PDFs
import os
import shutil
import pytesseract
from pathlib import Path
from pdf2image import convert_from_path
from loguru import logger

# -- Configure paths (auto-detect cloud vs local) --
IS_CLOUD = os.getenv("HOME", "").startswith("/home/adminuser")

if not IS_CLOUD:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    POPPLER_PATH = r"C:\Program Files\poppler-26.02.0\Library\bin"
else:
    POPPLER_PATH = None

if IS_CLOUD:
    import shutil as _sh
    pdftoppm = _sh.which("pdftoppm")
    POPPLER_PATH = str(Path(pdftoppm).parent) if pdftoppm else "/usr/bin"

def extract_text_from_pdf(pdf_path: str) -> str:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    logger.info(f"Converting PDF to images: {pdf_path.name}")
    convert_kwargs = {"dpi": 300}
    if POPPLER_PATH:
        convert_kwargs["poppler_path"] = POPPLER_PATH
    pages = convert_from_path(str(pdf_path), **convert_kwargs)
    logger.info(f"Extracted {len(pages)} pages from {pdf_path.name}")
    full_text = []
    for i, page in enumerate(pages):
        logger.info(f"Running OCR on page {i+1}/{len(pages)}")
        page_text = pytesseract.image_to_string(page, config="--psm 6")
        full_text.append(f"--- Page {i+1} ---
{page_text}")
    combined = "

".join(full_text)
    logger.success(f"OCR complete: {len(combined)} characters from {pdf_path.name}")
    return combined

def extract_text_from_directory(directory: str) -> dict:
    directory = Path(directory)
    pdf_files = list(directory.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {directory}")
        return {}
    results = {}
    for pdf_path in pdf_files:
        try:
            text = extract_text_from_pdf(str(pdf_path))
            results[pdf_path.name] = text
            logger.success(f"OCR done: {pdf_path.name}")
        except Exception as e:
            logger.error(f"OCR failed for {pdf_path.name}: {e}")
            results[pdf_path.name] = ""
    return results
