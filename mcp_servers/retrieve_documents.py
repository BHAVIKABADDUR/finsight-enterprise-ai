# mcp_servers/retrieve_documents.py
# MCP Server 4: Semantic document search via Qdrant
# Agents use this to find relevant documents by meaning not just keywords

import os
import json
import asyncio
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

load_dotenv()

server = Server("retrieve-documents")

# ── Clients ───────────────────────────────────────────────────────────────────
def get_qdrant():
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )

# Load embedding model once at startup
# This converts text into vectors for semantic search
print("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
COLLECTION_NAME = "finsight-documents"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 produces 384-dimensional vectors

def ensure_collection_exists(client: QdrantClient):
    """Create Qdrant collection if it doesn't exist."""
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if COLLECTION_NAME not in names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
        print(f"Created Qdrant collection: {COLLECTION_NAME}")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_documents",
            description=(
                "Search for relevant financial documents using semantic search. "
                "Returns documents most similar in meaning to the query, "
                "not just keyword matches."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="index_document",
            description=(
                "Index a document into the vector store for semantic search. "
                "Call this after processing a new document."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document UUID from the database"
                    },
                    "file_name": {
                        "type": "string",
                        "description": "The document filename"
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to index"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "Type of document: bank_statement, invoice, etc."
                    }
                },
                "required": ["document_id", "file_name", "content"]
            }
        )
    ]

@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:

    qdrant = get_qdrant()
    ensure_collection_exists(qdrant)

    if name == "search_documents":
        query = arguments["query"]
        top_k = arguments.get("top_k", 3)

        # Convert query to vector
        query_vector = embedding_model.encode(query).tolist()

        # Search Qdrant
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
                "content_preview": r.payload.get("content", "")[:200]
            })

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "query": query,
                "results": formatted
            }, indent=2)
        )]

    elif name == "index_document":
        document_id = arguments["document_id"]
        content = arguments["content"]
        file_name = arguments["file_name"]
        file_type = arguments.get("file_type", "unknown")

        # Convert content to vector
        vector = embedding_model.encode(content).tolist()

        # Store in Qdrant
        import hashlib
        point_id = int(
            hashlib.md5(document_id.encode()).hexdigest()[:8], 16
        )

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
                        "content": content[:500]
                    }
                )
            ]
        )

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "status": "indexed",
                "document_id": document_id,
                "file_name": file_name,
                "vector_dimensions": len(vector)
            }, indent=2)
        )]

    else:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())