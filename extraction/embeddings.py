# extraction/embeddings.py
# Indexes documents into Qdrant for semantic search
# Converts text into vectors using sentence-transformers

import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from supabase import create_client
from loguru import logger

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
COLLECTION_NAME = "finsight-documents"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output size

# ── Clients ───────────────────────────────────────────────────────────────────
def get_qdrant():
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

# Load model once
logger.info("Loading sentence transformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
logger.success("Model loaded")

# ── Collection setup ──────────────────────────────────────────────────────────
def ensure_collection(client: QdrantClient):
    """Create collection if it doesn't exist."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
        logger.success(f"Created Qdrant collection: {COLLECTION_NAME}")
    else:
        logger.info(f"Collection already exists: {COLLECTION_NAME}")

# ── Index one document ────────────────────────────────────────────────────────
def index_document(
    document_id: str,
    file_name: str,
    file_type: str,
    text_content: str
):
    """
    Convert document text to vector and store in Qdrant.
    
    Args:
        document_id: Supabase document UUID
        file_name: Original filename
        file_type: bank_statement, invoice, etc.
        text_content: Full text content to embed
    """
    qdrant = get_qdrant()
    ensure_collection(qdrant)
    
    # Truncate to 512 chars for embedding
    # (model has a token limit, and first 512 chars capture the most important info)
    content_to_embed = text_content[:512]
    
    # Convert text to vector
    logger.info(f"Generating embedding for: {file_name}")
    vector = model.encode(content_to_embed).tolist()
    
    # Generate integer ID from UUID using MD5
    point_id = int(hashlib.md5(document_id.encode()).hexdigest()[:8], 16)
    
    # Store in Qdrant
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "document_id": document_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "content_preview": text_content[:300],
                    "char_count": len(text_content)
                }
            )
        ]
    )
    
    logger.success(f"Indexed: {file_name} (vector dim: {len(vector)})")
    return point_id

# ── Search documents ──────────────────────────────────────────────────────────
def search_documents(query: str, top_k: int = 3) -> list:
    """
    Search for documents semantically similar to the query.
    
    Args:
        query: Natural language search query
        top_k: Number of results to return
        
    Returns:
        List of matching documents with scores
    """
    qdrant = get_qdrant()
    ensure_collection(qdrant)
    
    # Embed the query
    query_vector = model.encode(query).tolist()
    
    # Search
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )
    
    formatted = []
    for r in results:
        formatted.append({
            "document_id": r.payload.get("document_id"),
            "file_name": r.payload.get("file_name"),
            "file_type": r.payload.get("file_type"),
            "relevance_score": round(r.score, 4),
            "content_preview": r.payload.get("content_preview", "")
        })
    
    return formatted

# ── Index all documents from Supabase ─────────────────────────────────────────
def index_all_documents():
    """
    Index all documents from the database into Qdrant.
    Uses OCR text for PDFs and raw content for CSVs.
    """
    from extraction.ocr import extract_text_from_pdf
    
    supabase = get_supabase()
    
    # Get all documents
    result = supabase.table("documents").select("*").execute()
    documents = result.data
    
    if not documents:
        logger.warning("No documents found in database")
        return []
    
    logger.info(f"Indexing {len(documents)} documents into Qdrant...")
    
    indexed = []
    for doc in documents:
        document_id = doc["id"]
        file_name = doc["file_name"]
        file_type = doc["file_type"]
        local_path = f"data/raw/{file_name}"
        
        try:
            # Get text content based on file type
            if file_name.endswith(".pdf"):
                text_content = extract_text_from_pdf(local_path)
            elif file_name.endswith(".csv"):
                with open(local_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            else:
                logger.warning(f"Unsupported file type: {file_name}")
                continue
            
            # Index into Qdrant
            point_id = index_document(
                document_id=document_id,
                file_name=file_name,
                file_type=file_type,
                text_content=text_content
            )
            
            indexed.append({
                "file_name": file_name,
                "file_type": file_type,
                "point_id": point_id,
                "status": "indexed"
            })
            
        except Exception as e:
            logger.error(f"Failed to index {file_name}: {e}")
            indexed.append({
                "file_name": file_name,
                "status": "failed",
                "error": str(e)
            })
    
    return indexed

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting Qdrant document indexing...")
    
    # Index all documents
    results = index_all_documents()
    
    print("\n── Indexing Results ──")
    for r in results:
        status = r.get("status")
        name = r.get("file_name")
        print(f"  {name}: {status}")
    
    successful = [r for r in results if r.get("status") == "indexed"]
    print(f"\n✅ Indexed {len(successful)}/{len(results)} documents")
    
    # Test semantic search
    print("\n── Semantic Search Test ──")
    test_queries = [
        "bank account statement UAE",
        "invoice payment vendor",
        "financial transactions debit credit"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        search_results = search_documents(query, top_k=2)
        for r in search_results:
            print(
                f"  → {r['file_name']} "
                f"(score: {r['relevance_score']}, "
                f"type: {r['file_type']})"
            )
    
    print("\n✅ Qdrant indexing and search complete")