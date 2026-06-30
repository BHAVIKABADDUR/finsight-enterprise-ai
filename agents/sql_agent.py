# agents/sql_agent.py
# Natural Language to SQL Agent
# Converts plain English questions into safe, read-only Supabase queries

import os
import re
import json
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client
from loguru import logger

load_dotenv()

def get_groq():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

# ── Schema description for the LLM ────────────────────────────────────────────
SCHEMA_DESCRIPTION = """
Available table: transactions

Columns:
- id (uuid)
- document_id (uuid)
- transaction_date (date) - format YYYY-MM-DD
- description (text)
- amount (numeric) - in AED
- currency (text)
- transaction_type (text) - 'credit' or 'debit'
- category (text) - e.g. 'Salary', 'Vendor Payment', 'Transfer', 'Utility Bill', 'Rent', 'Insurance', 'Government Fee', 'Subscription', 'Retail Purchase'
- account_number (text)
- confidence_score (numeric)
- is_flagged (boolean)
- flag_reason (text)
- created_at (timestamptz)
"""

SQL_AGENT_PROMPT = f"""You are a SQL query planner for a financial database.

{SCHEMA_DESCRIPTION}

Convert the user's natural language question into a structured filter specification.
You do NOT write raw SQL — you output a JSON filter specification that will be 
safely applied to a Supabase query.

Return ONLY a JSON object with this structure:
{{
    "filters": [
        {{"column": "amount", "operator": "gt", "value": 10000}},
        {{"column": "category", "operator": "eq", "value": "Transfer"}}
    ],
    "order_by": "amount",
    "order_direction": "desc",
    "limit": 50,
    "explanation": "brief explanation of what this query does"
}}

Valid operators: eq, neq, gt, gte, lt, lte, like
Valid columns: transaction_date, description, amount, currency, transaction_type, category, is_flagged, flag_reason

Rules:
- Only use columns that exist in the schema
- For text search use 'like' operator with value wrapped in %value%
- Always include a reasonable limit (default 50, max 200)
- If the question is about flagged/suspicious items, filter is_flagged = true
- Return ONLY the JSON, no explanation outside the JSON
"""

def natural_language_to_filter(question: str) -> dict:
    """
    Convert a natural language question into a structured filter.
    
    Args:
        question: User's question in plain English
        
    Returns:
        Filter specification dict
    """
    client = get_groq()

    logger.info(f"Converting to SQL filter: {question}")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SQL_AGENT_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0,
        max_tokens=500
    )

    content = response.choices[0].message.content

    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        filter_spec = json.loads(content[start:end])
    except Exception as e:
        logger.error(f"Failed to parse filter spec: {e}")
        filter_spec = {
            "filters": [],
            "order_by": "transaction_date",
            "order_direction": "desc",
            "limit": 20,
            "explanation": "Could not parse query, showing recent transactions"
        }

    logger.success(f"Filter generated: {filter_spec.get('explanation', '')}")
    return filter_spec

# ── Safe query builder ────────────────────────────────────────────────────────
ALLOWED_COLUMNS = {
    "transaction_date", "description", "amount", "currency",
    "transaction_type", "category", "is_flagged", "flag_reason"
}

ALLOWED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "like"}

def execute_safe_query(filter_spec: dict) -> dict:
    """
    Execute a SELECT-only query against the transactions table
    based on a validated filter specification.
    
    This NEVER allows raw SQL execution — only structured,
    validated filters through the Supabase query builder.
    
    Args:
        filter_spec: Filter specification from natural_language_to_filter()
        
    Returns:
        Query results with metadata
    """
    supabase = get_supabase()
    query = supabase.table("transactions").select("*")

    applied_filters = []

    for f in filter_spec.get("filters", []):
        column = f.get("column")
        operator = f.get("operator")
        value = f.get("value")

        # Security: only allow whitelisted columns and operators
        if column not in ALLOWED_COLUMNS:
            logger.warning(f"Rejected filter on disallowed column: {column}")
            continue
        if operator not in ALLOWED_OPERATORS:
            logger.warning(f"Rejected filter with disallowed operator: {operator}")
            continue

        if operator == "eq":
            query = query.eq(column, value)
        elif operator == "neq":
            query = query.neq(column, value)
        elif operator == "gt":
            query = query.gt(column, value)
        elif operator == "gte":
            query = query.gte(column, value)
        elif operator == "lt":
            query = query.lt(column, value)
        elif operator == "lte":
            query = query.lte(column, value)
        elif operator == "like":
            query = query.like(column, value)

        applied_filters.append(f"{column} {operator} {value}")

    # Order by
    order_by = filter_spec.get("order_by", "transaction_date")
    if order_by not in ALLOWED_COLUMNS and order_by != "transaction_date":
        order_by = "transaction_date"

    order_direction = filter_spec.get("order_direction", "desc")
    query = query.order(order_by, desc=(order_direction == "desc"))

    # Limit (capped at 200 for safety)
    limit = min(filter_spec.get("limit", 50), 200)
    query = query.limit(limit)

    logger.info(f"Executing safe query with filters: {applied_filters}")

    result = query.execute()

    return {
        "results": result.data,
        "count": len(result.data),
        "applied_filters": applied_filters,
        "explanation": filter_spec.get("explanation", "")
    }

# ── Full pipeline ──────────────────────────────────────────────────────────────
def query_with_natural_language(question: str) -> dict:
    """
    Full pipeline: natural language question → filter spec → safe query → results
    
    Args:
        question: Natural language question
        
    Returns:
        Query results with explanation
    """
    filter_spec = natural_language_to_filter(question)
    results = execute_safe_query(filter_spec)

    return {
        "question": question,
        "explanation": results["explanation"],
        "applied_filters": results["applied_filters"],
        "result_count": results["count"],
        "results": results["results"]
    }

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_questions = [
        "Show me all transactions over AED 10,000",
        "What flagged transactions do we have?",
        "Show me all debit transactions in the Transfer category"
    ]

    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print('='*60)

        result = query_with_natural_language(question)

        print(f"Explanation: {result['explanation']}")
        print(f"Filters applied: {result['applied_filters']}")
        print(f"Results found: {result['result_count']}")

        for r in result["results"][:5]:
            print(
                f"  {r['transaction_date']} | "
                f"{r['description'][:30]} | "
                f"AED {float(r['amount']):,.2f} | "
                f"{r['category']}"
            )