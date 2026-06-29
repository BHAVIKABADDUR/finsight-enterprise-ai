# pipeline/bronze.py
# Bronze Layer — Raw file ingestion into Supabase Storage
# Stores original files untouched + creates document registry entry

import os
import uuid
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from loguru import logger

load_dotenv()

# ── Supabase client ───────────────────────────────────────────────────────────
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    return create_client(url, key)

# ── File type detector ────────────────────────────────────────────────────────
def detect_file_type(filename: str) -> str:
    """
    Detect what kind of financial document this is
    based on the filename.
    """
    filename_lower = filename.lower()
    if "bank_statement" in filename_lower or "statement" in filename_lower:
        return "bank_statement"
    elif "invoice" in filename_lower:
        return "invoice"
    elif "transaction" in filename_lower or filename_lower.endswith(".csv"):
        return "transaction_csv"
    elif "report" in filename_lower:
        return "financial_report"
    else:
        return "unknown"

# ── Core bronze ingestion function ───────────────────────────────────────────
def ingest_file_to_bronze(file_path: str) -> dict:
    """
    Ingest a single file into the Bronze layer.
    
    What this does:
    1. Reads the file from local disk
    2. Uploads it to Supabase Storage (raw-documents bucket)
    3. Creates a record in the documents table
    4. Returns document metadata including the new document ID
    
    Args:
        file_path: Path to the local file to ingest
        
    Returns:
        dict with document_id, file_name, file_type, status
    """
    supabase = get_supabase_client()
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_name = file_path.name
    file_type = detect_file_type(file_name)
    document_id = str(uuid.uuid4())
    
    logger.info(f"Starting bronze ingestion for: {file_name}")
    logger.info(f"Detected file type: {file_type}")
    
    # ── Step 1: Upload file to Supabase Storage ───────────────────────────
    storage_path = f"bronze/{document_id}/{file_name}"
    
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    
    # Determine content type
    if file_name.endswith(".pdf"):
        content_type = "application/pdf"
    elif file_name.endswith(".csv"):
        content_type = "text/csv"
    else:
        content_type = "application/octet-stream"
    
    logger.info(f"Uploading to Supabase Storage: {storage_path}")
    
    supabase.storage.from_("raw-documents").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type}
    )
    
    logger.success(f"File uploaded to storage: {storage_path}")
    
    # ── Step 2: Create document record in database ────────────────────────
    document_record = {
        "id": document_id,
        "file_name": file_name,
        "file_type": file_type,
        "file_path": storage_path,
        "status": "pending",
        "metadata": {
            "file_size_bytes": len(file_bytes),
            "ingested_at": datetime.utcnow().isoformat(),
            "source": "synthetic_data_generator"
        }
    }
    
    result = supabase.table("documents").insert(document_record).execute()
    
    logger.success(f"Document record created with ID: {document_id}")
    
    return {
        "document_id": document_id,
        "file_name": file_name,
        "file_type": file_type,
        "storage_path": storage_path,
        "status": "pending"
    }

# ── Batch ingestion ───────────────────────────────────────────────────────────
def ingest_directory_to_bronze(directory: str) -> list:
    """
    Ingest all files from a directory into the Bronze layer.
    
    Args:
        directory: Path to directory containing files to ingest
        
    Returns:
        List of document metadata dicts
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    # Supported file types
    supported_extensions = {".pdf", ".csv", ".xlsx", ".txt"}
    files = [
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in supported_extensions
    ]
    
    if not files:
        logger.warning(f"No supported files found in {directory}")
        return []
    
    logger.info(f"Found {len(files)} files to ingest from {directory}")
    
    results = []
    for file_path in files:
        try:
            result = ingest_file_to_bronze(str(file_path))
            results.append(result)
            logger.success(f"✅ Ingested: {file_path.name}")
        except Exception as e:
            logger.error(f"❌ Failed to ingest {file_path.name}: {e}")
            results.append({
                "file_name": file_path.name,
                "status": "failed",
                "error": str(e)
            })
    
    return results

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting Bronze Layer ingestion...")
    
    results = ingest_directory_to_bronze("data/raw")
    
    print("\n── Bronze Ingestion Results ──")
    for r in results:
        status = r.get("status", "unknown")
        name = r.get("file_name", "unknown")
        doc_id = r.get("document_id", "N/A")
        print(f"  {name}: {status} (ID: {doc_id})")
    
    successful = [r for r in results if r.get("status") == "pending"]
    print(f"\n✅ Successfully ingested: {len(successful)}/{len(results)} files")