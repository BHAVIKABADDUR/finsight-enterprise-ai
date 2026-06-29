# extraction/llm_extractor.py
# LLM extraction layer — uses Groq/Llama to extract structured data from OCR text
# Pydantic validates the output structure

import os
import json
import uuid
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from groq import Groq
from supabase import create_client
from loguru import logger

load_dotenv()

# ── Pydantic models — define the structure we expect ─────────────────────────
class ExtractedTransaction(BaseModel):
    """Single transaction extracted from a document."""
    date: Optional[str] = Field(None, description="Transaction date YYYY-MM-DD")
    description: Optional[str] = Field(None, description="Transaction description")
    amount: Optional[float] = Field(None, description="Transaction amount")
    transaction_type: Optional[str] = Field(None, description="credit or debit")
    category: Optional[str] = Field(None, description="Transaction category")
    currency: str = Field("AED", description="Currency code")

class ExtractedBankStatement(BaseModel):
    """Structured data extracted from a bank statement."""
    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None
    statement_period: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    currency: str = "AED"
    transactions: List[ExtractedTransaction] = []

class ExtractedInvoice(BaseModel):
    """Structured data extracted from an invoice."""
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    bill_to: Optional[str] = None
    subtotal: Optional[float] = None
    vat_amount: Optional[float] = None
    total_due: Optional[float] = None
    currency: str = "AED"
    payment_iban: Optional[str] = None

# ── Groq client ───────────────────────────────────────────────────────────────
def get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

# ── LLM extraction prompts ────────────────────────────────────────────────────
BANK_STATEMENT_PROMPT = """You are a financial document extraction specialist.
Extract structured data from this bank statement OCR text.

Return ONLY a valid JSON object with this exact structure:
{
    "account_holder": "name or null",
    "account_number": "number or null", 
    "iban": "IBAN or null",
    "statement_period": "period string or null",
    "opening_balance": 0.00,
    "closing_balance": 0.00,
    "currency": "AED",
    "transactions": [
        {
            "date": "YYYY-MM-DD or null",
            "description": "description",
            "amount": 0.00,
            "transaction_type": "credit or debit",
            "category": "category",
            "currency": "AED"
        }
    ]
}

Rules:
- Extract ALL transactions you can find
- Amounts must be numbers, not strings
- Dates must be YYYY-MM-DD format
- If a field is not found, use null
- Return ONLY the JSON, no explanation
"""

INVOICE_PROMPT = """You are a financial document extraction specialist.
Extract structured data from this invoice OCR text.

Return ONLY a valid JSON object with this exact structure:
{
    "vendor_name": "name or null",
    "invoice_number": "number or null",
    "invoice_date": "YYYY-MM-DD or null",
    "due_date": "YYYY-MM-DD or null",
    "bill_to": "name or null",
    "subtotal": 0.00,
    "vat_amount": 0.00,
    "total_due": 0.00,
    "currency": "AED",
    "payment_iban": "IBAN or null"
}

Rules:
- Amounts must be numbers, not strings
- Dates must be YYYY-MM-DD format
- If a field is not found, use null
- Return ONLY the JSON, no explanation
"""

# ── Core extraction function ──────────────────────────────────────────────────
def extract_with_llm(
    ocr_text: str,
    document_type: str
) -> dict:
    """
    Use Groq/Llama to extract structured data from OCR text.
    
    Args:
        ocr_text: Raw text from OCR
        document_type: 'bank_statement' or 'invoice'
        
    Returns:
        Extracted structured data as dict
    """
    client = get_groq_client()
    
    if document_type == "bank_statement":
        prompt = BANK_STATEMENT_PROMPT
    elif document_type == "invoice":
        prompt = INVOICE_PROMPT
    else:
        prompt = BANK_STATEMENT_PROMPT
    
    logger.info(f"Running LLM extraction for {document_type}...")
    
    start_time = datetime.utcnow()
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Extract from this document:\n\n{ocr_text}"}
        ],
        temperature=0,
        max_tokens=2000
    )
    
    end_time = datetime.utcnow()
    extraction_time_ms = int(
        (end_time - start_time).total_seconds() * 1000
    )
    tokens_used = response.usage.total_tokens
    
    raw_content = response.choices[0].message.content
    
    # Parse JSON response
    try:
        # Find JSON block
        start = raw_content.find("{")
        end = raw_content.rfind("}") + 1
        json_str = raw_content[start:end]
        extracted = json.loads(json_str)
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        extracted = {}
    
    logger.success(
        f"LLM extraction complete: "
        f"{tokens_used} tokens, "
        f"{extraction_time_ms}ms"
    )
    
    return {
        "extracted_fields": extracted,
        "extraction_time_ms": extraction_time_ms,
        "tokens_used": tokens_used,
        "model_used": "llama-3.3-70b-versatile"
    }

# ── Validate with Pydantic ────────────────────────────────────────────────────
def validate_extraction(
    extracted: dict,
    document_type: str
) -> tuple:
    """
    Validate extracted data using Pydantic models.
    
    Returns:
        (validated_data, confidence_score)
    """
    try:
        if document_type == "bank_statement":
            validated = ExtractedBankStatement(**extracted)
            # Confidence based on how many fields were extracted
            filled_fields = sum(
                1 for v in extracted.values()
                if v is not None and v != [] and v != {}
            )
            total_fields = 8
            confidence = round(filled_fields / total_fields, 2)
            
        elif document_type == "invoice":
            validated = ExtractedInvoice(**extracted)
            filled_fields = sum(
                1 for v in extracted.values()
                if v is not None
            )
            total_fields = 9
            confidence = round(filled_fields / total_fields, 2)
        else:
            return extracted, 0.5
            
        return validated.model_dump(), confidence
        
    except Exception as e:
        logger.warning(f"Pydantic validation warning: {e}")
        return extracted, 0.5

# ── Save to Supabase ──────────────────────────────────────────────────────────
def save_extraction_result(
    document_id: str,
    extracted_fields: dict,
    confidence_scores: dict,
    model_used: str,
    extraction_time_ms: int,
    tokens_used: int
):
    """Save extraction results to the extraction_results table."""
    supabase = get_supabase()
    
    record = {
        "id": str(uuid.uuid4()),
        "document_id": document_id,
        "extracted_fields": extracted_fields,
        "confidence_scores": confidence_scores,
        "model_used": model_used,
        "extraction_time_ms": extraction_time_ms,
        "tokens_used": tokens_used,
        "created_at": datetime.utcnow().isoformat()
    }
    
    supabase.table("extraction_results").insert(record).execute()
    logger.success(f"Extraction result saved for document: {document_id}")
    
    # Update document status
    supabase.table("documents").update({
        "status": "extracted",
        "processed_at": datetime.utcnow().isoformat()
    }).eq("id", document_id).execute()

# ── Full pipeline for one document ────────────────────────────────────────────
def extract_document(
    document_id: str,
    file_path: str,
    document_type: str
) -> dict:
    """
    Run the full extraction pipeline for one document:
    1. OCR → raw text
    2. LLM → structured JSON
    3. Pydantic → validated data
    4. Supabase → saved result
    
    Args:
        document_id: Supabase document ID
        file_path: Local path to PDF
        document_type: 'bank_statement' or 'invoice'
        
    Returns:
        Extraction result summary
    """
    from extraction.ocr import extract_text_from_pdf
    
    logger.info(f"Starting full extraction for: {file_path}")
    
    # Step 1: OCR
    ocr_text = extract_text_from_pdf(file_path)
    
    if not ocr_text.strip():
        logger.error("OCR returned empty text")
        return {"status": "failed", "reason": "OCR returned empty text"}
    
    # Step 2: LLM extraction
    llm_result = extract_with_llm(ocr_text, document_type)
    extracted_fields = llm_result["extracted_fields"]
    
    # Step 3: Pydantic validation
    validated_fields, confidence = validate_extraction(
        extracted_fields, document_type
    )
    
    confidence_scores = {
        "overall": confidence,
        "ocr_quality": min(1.0, len(ocr_text) / 500),
        "llm_extraction": confidence
    }
    
    logger.info(f"Confidence score: {confidence}")
    
    # Step 4: Save to Supabase
    save_extraction_result(
        document_id=document_id,
        extracted_fields=validated_fields,
        confidence_scores=confidence_scores,
        model_used=llm_result["model_used"],
        extraction_time_ms=llm_result["extraction_time_ms"],
        tokens_used=llm_result["tokens_used"]
    )
    
    return {
        "document_id": document_id,
        "document_type": document_type,
        "extracted_fields": validated_fields,
        "confidence": confidence,
        "tokens_used": llm_result["tokens_used"],
        "extraction_time_ms": llm_result["extraction_time_ms"],
        "status": "extracted"
    }

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from supabase import create_client
    
    supabase = get_supabase()
    
    logger.info("Starting LLM extraction pipeline for PDF documents...")
    
    # Get PDF documents from Supabase
    result = supabase.table("documents").select("*").in_(
        "file_type", ["bank_statement", "invoice"]
    ).execute()
    
    documents = result.data
    
    if not documents:
        logger.warning("No PDF documents found in database")
        exit(0)
    
    logger.info(f"Found {len(documents)} PDF documents to extract")
    
    results = []
    for doc in documents:
        document_id = doc["id"]
        file_name = doc["file_name"]
        document_type = doc["file_type"]
        local_path = f"data/raw/{file_name}"
        
        logger.info(f"Processing: {file_name} ({document_type})")
        
        try:
            result = extract_document(
                document_id=document_id,
                file_path=local_path,
                document_type=document_type
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to extract {file_name}: {e}")
    
    print("\n── Extraction Results ──")
    for r in results:
        print(f"\n  {r.get('document_type', 'unknown').upper()}")
        print(f"  Confidence: {r.get('confidence', 0):.0%}")
        print(f"  Tokens used: {r.get('tokens_used', 0)}")
        print(f"  Time: {r.get('extraction_time_ms', 0)}ms")
        
        fields = r.get("extracted_fields", {})
        if "account_holder" in fields:
            print(f"  Account Holder: {fields.get('account_holder')}")
            print(f"  IBAN: {fields.get('iban')}")
            print(f"  Closing Balance: AED {fields.get('closing_balance')}")
        elif "vendor_name" in fields:
            print(f"  Vendor: {fields.get('vendor_name')}")
            print(f"  Invoice: {fields.get('invoice_number')}")
            print(f"  Total Due: AED {fields.get('total_due')}")
    
    print(f"\n✅ Extraction complete for {len(results)} documents")