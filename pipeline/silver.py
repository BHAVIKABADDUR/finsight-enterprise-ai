# pipeline/silver.py
# Silver Layer — Data cleaning, validation, and standardization
# Takes raw Bronze data and produces clean structured records

import os
import re
import csv
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
    return create_client(url, key)

# ── Data cleaning functions ───────────────────────────────────────────────────
def clean_amount(amount_str) -> float:
    """
    Clean and convert amount to float.
    Handles: '1,234.56', '$1234', 'AED 1234', 1234.56
    """
    if isinstance(amount_str, (int, float)):
        return round(float(amount_str), 2)
    
    # Remove currency symbols, commas, spaces
    cleaned = re.sub(r'[^\d.]', '', str(amount_str))
    
    if not cleaned:
        return 0.0
    
    try:
        return round(float(cleaned), 2)
    except ValueError:
        logger.warning(f"Could not parse amount: {amount_str}, defaulting to 0.0")
        return 0.0

def clean_date(date_str) -> str:
    """
    Standardize date to YYYY-MM-DD format.
    Handles multiple common date formats.
    """
    if not date_str:
        return datetime.utcnow().strftime("%Y-%m-%d")
    
    date_formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%B %d, %Y"
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}, using today")
    return datetime.utcnow().strftime("%Y-%m-%d")

def clean_text(text_str) -> str:
    """Clean text fields — strip whitespace, normalize spaces."""
    if not text_str:
        return ""
    return " ".join(str(text_str).strip().split())

def clean_transaction_type(type_str) -> str:
    """Standardize transaction type to 'credit' or 'debit'."""
    if not type_str:
        return "debit"
    
    type_lower = str(type_str).lower().strip()
    
    if type_lower in ["credit", "cr", "c", "in", "deposit"]:
        return "credit"
    elif type_lower in ["debit", "dr", "d", "out", "withdrawal"]:
        return "debit"
    else:
        return "debit"  # default

# ── Anomaly detection ─────────────────────────────────────────────────────────
def detect_anomalies(transaction: dict, all_transactions: list) -> tuple:
    """
    Detect anomalies in a transaction.
    
    Returns:
        (is_flagged: bool, flag_reason: str)
    """
    amount = transaction.get("amount", 0)
    description = transaction.get("description", "")
    
    # Rule 1: Unusually large amount (over AED 75,000)
    if amount > 75000:
        return True, f"Unusually large transaction: AED {amount:,.2f}"
    
    # Rule 2: Suspicious round numbers over AED 10,000
    if amount >= 10000 and amount % 1000 == 0:
        return True, f"Suspicious round number transaction: AED {amount:,.2f}"
    
    # Rule 3: Duplicate detection
    # Check if same description + amount exists elsewhere
    duplicates = [
        t for t in all_transactions
        if t.get("description") == description
        and t.get("amount") == amount
        and t is not transaction
    ]
    if duplicates:
        return True, f"Duplicate transaction detected: {description} - AED {amount:,.2f}"
    
    # Rule 4: Unknown vendor
    if "UNKNOWN" in description.upper():
        return True, f"Unknown vendor: {description}"
    
    # Rule 5: Zero or negative amount
    if amount <= 0:
        return True, f"Invalid transaction amount: {amount}"
    
    return False, None

# ── CSV processor ─────────────────────────────────────────────────────────────
def process_csv_to_silver(
    document_id: str,
    file_path: str
) -> list:
    """
    Process a transaction CSV file through the Silver layer.
    
    Args:
        document_id: The Bronze layer document ID
        file_path: Path to the local CSV file
        
    Returns:
        List of cleaned transaction records ready for database insert
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    logger.info(f"Processing CSV: {file_path.name}")
    
    # Read raw CSV
    raw_transactions = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_transactions.append(dict(row))
    
    logger.info(f"Read {len(raw_transactions)} raw transactions")
    
    # Clean each transaction
    cleaned_transactions = []
    for raw in raw_transactions:
        cleaned = {
            "description": clean_text(raw.get("description", "")),
            "amount": clean_amount(raw.get("amount", 0)),
            "transaction_date": clean_date(raw.get("date", "")),
            "transaction_type": clean_transaction_type(raw.get("type", "")),
            "category": clean_text(raw.get("category", "Unknown")),
            "currency": clean_text(raw.get("currency", "AED")).upper(),
        }
        cleaned_transactions.append(cleaned)
    
    logger.info(f"Cleaned {len(cleaned_transactions)} transactions")
    
    # Run anomaly detection on all transactions together
    # (needed for duplicate detection across the full set)
    silver_records = []
    flagged_count = 0
    
    for txn in cleaned_transactions:
        is_flagged, flag_reason = detect_anomalies(txn, cleaned_transactions)
        
        if is_flagged:
            flagged_count += 1
            logger.warning(f"🚩 Flagged: {flag_reason}")
        
        silver_record = {
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "transaction_date": txn["transaction_date"],
            "description": txn["description"],
            "amount": txn["amount"],
            "currency": txn["currency"],
            "transaction_type": txn["transaction_type"],
            "category": txn["category"],
            "confidence_score": 1.0,  # CSV data = high confidence
            "is_flagged": is_flagged,
            "flag_reason": flag_reason
        }
        silver_records.append(silver_record)
    
    logger.success(
        f"Silver processing complete: "
        f"{len(silver_records)} records, "
        f"{flagged_count} flagged"
    )
    
    return silver_records

# ── Database writer ───────────────────────────────────────────────────────────
def write_to_silver(document_id: str, file_path: str) -> dict:
    """
    Full Silver layer pipeline for one document:
    1. Process and clean the data
    2. Write to transactions table
    3. Update document status to 'silver_complete'
    
    Args:
        document_id: Bronze layer document ID
        file_path: Local path to the file
        
    Returns:
        Summary dict with counts and stats
    """
    supabase = get_supabase_client()
    
    file_path = Path(file_path)
    
    # Only process CSVs in Silver layer
    # PDFs go through LLM extraction (next step)
    if file_path.suffix.lower() != ".csv":
        logger.info(f"Skipping non-CSV file in Silver layer: {file_path.name}")
        logger.info(f"PDFs will be processed by LLM extraction pipeline")
        return {
            "document_id": document_id,
            "file_name": file_path.name,
            "status": "skipped",
            "reason": "PDF files processed by LLM extraction"
        }
    
    # Process CSV
    silver_records = process_csv_to_silver(document_id, str(file_path))
    
    if not silver_records:
        logger.warning("No records to write")
        return {"document_id": document_id, "records_written": 0}
    
    # Write to Supabase in batches of 50
    batch_size = 50
    total_written = 0
    
    for i in range(0, len(silver_records), batch_size):
        batch = silver_records[i:i + batch_size]
        supabase.table("transactions").insert(batch).execute()
        total_written += len(batch)
        logger.info(f"Written batch: {total_written}/{len(silver_records)}")
    
    # Update document status
    supabase.table("documents").update({
        "status": "silver_complete",
        "processed_at": datetime.utcnow().isoformat()
    }).eq("id", document_id).execute()
    
    logger.success(f"Document {document_id} status updated to silver_complete")
    
    flagged = [r for r in silver_records if r["is_flagged"]]
    
    return {
        "document_id": document_id,
        "file_name": file_path.name,
        "records_written": total_written,
        "flagged_count": len(flagged),
        "status": "silver_complete"
    }

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    supabase = get_supabase_client()
    
    logger.info("Starting Silver Layer processing...")
    
    # Get all pending documents from Bronze
    result = supabase.table("documents").select("*").eq(
        "status", "pending"
    ).execute()
    
    documents = result.data
    
    if not documents:
        logger.warning("No pending documents found in Bronze layer")
        exit(0)
    
    logger.info(f"Found {len(documents)} pending documents")
    
    results = []
    for doc in documents:
        document_id = doc["id"]
        file_name = doc["file_name"]
        local_path = f"data/raw/{file_name}"
        
        logger.info(f"Processing: {file_name}")
        result = write_to_silver(document_id, local_path)
        results.append(result)
    
    print("\n── Silver Layer Results ──")
    for r in results:
        print(f"  {r.get('file_name')}: "
              f"{r.get('records_written', 0)} records, "
              f"{r.get('flagged_count', 0)} flagged, "
              f"status: {r.get('status')}")
    
    print(f"\n✅ Silver layer complete")