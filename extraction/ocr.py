# extraction/ocr.py
# OCR layer — converts PDF pages to text using Tesseract
# Handles both text-based and scanned PDFs

import os
import pytesseract
from pathlib import Path
from pdf2image import convert_from_path
from loguru import logger

# ── Configure paths ───────────────────────────────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler-26.02.0\Library\bin"

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file using OCR.
    
    Process:
    1. Convert each PDF page to an image
    2. Run Tesseract OCR on each image
    3. Combine all page text into one string
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Full extracted text as a single string
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    logger.info(f"Converting PDF to images: {pdf_path.name}")
    
    # Convert PDF pages to images
    pages = convert_from_path(
        str(pdf_path),
        dpi=300,  # Higher DPI = better OCR accuracy
        poppler_path=POPPLER_PATH
    )
    
    logger.info(f"Extracted {len(pages)} pages from {pdf_path.name}")
    
    # Run OCR on each page
    full_text = []
    for i, page in enumerate(pages):
        logger.info(f"Running OCR on page {i+1}/{len(pages)}")
        page_text = pytesseract.image_to_string(
            page,
            config="--psm 6"  # Assume uniform block of text
        )
        full_text.append(f"--- Page {i+1} ---\n{page_text}")
    
    combined = "\n\n".join(full_text)
    logger.success(
        f"OCR complete: {len(combined)} characters extracted from {pdf_path.name}"
    )
    
    return combined

def extract_text_from_directory(directory: str) -> dict:
    """
    Extract text from all PDFs in a directory.
    
    Returns:
        Dict mapping filename to extracted text
    """
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
            logger.success(f"✅ OCR done: {pdf_path.name}")
        except Exception as e:
            logger.error(f"❌ OCR failed for {pdf_path.name}: {e}")
            results[pdf_path.name] = ""
    
    return results

if __name__ == "__main__":
    logger.info("Testing OCR on synthetic PDFs...")
    results = extract_text_from_directory("data/raw")
    
    for filename, text in results.items():
        print(f"\n── {filename} ──")
        print(text[:500])
        print("...")