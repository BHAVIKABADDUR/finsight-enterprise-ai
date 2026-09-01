import os, shutil, pytesseract
from pathlib import Path
from pdf2image import convert_from_path
from loguru import logger

IS_CLOUD = os.getenv("HOME", "").startswith("/home/adminuser")

if not IS_CLOUD:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    POPPLER_PATH = r"C:\Program Files\poppler-26.02.0\Library\bin"
else:
    p = shutil.which("pdftoppm")
    POPPLER_PATH = str(Path(p).parent) if p else "/usr/bin"


def extract_text_from_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError("PDF not found: " + str(pdf_path))
    kw = {"dpi": 300}
    if POPPLER_PATH:
        kw["poppler_path"] = POPPLER_PATH
    pages = convert_from_path(str(pdf_path), **kw)
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
