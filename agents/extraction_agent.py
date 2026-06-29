# agents/extraction_agent.py
# Pulls relevant financial data using MCP tools
# Feeds cleaned data to the Analysis Agent

import os
import json
import asyncio
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from supabase import create_client
from agents.state import FinSightState

load_dotenv()

def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

def fetch_transactions(flagged_only: bool = False) -> dict:
    """Fetch transactions directly from Supabase."""
    supabase = get_supabase()
    
    query = supabase.table("transactions").select("*")
    if flagged_only:
        query = query.eq("is_flagged", True)
    
    result = query.limit(50).execute()
    transactions = result.data
    
    total_credit = sum(
        float(t["amount"]) for t in transactions
        if t["transaction_type"] == "credit"
    )
    total_debit = sum(
        float(t["amount"]) for t in transactions
        if t["transaction_type"] == "debit"
    )
    flagged = [t for t in transactions if t["is_flagged"]]
    
    return {
        "transactions": transactions,
        "summary": {
            "total_count": len(transactions),
            "total_credit_aed": round(total_credit, 2),
            "total_debit_aed": round(total_debit, 2),
            "flagged_count": len(flagged)
        },
        "flagged_transactions": flagged
    }

def fetch_kpis() -> dict:
    """Fetch Gold layer KPIs from Supabase."""
    supabase = get_supabase()
    
    categories = supabase.table("gold_spend_by_category").select(
        "*"
    ).order("total_amount", desc=True).limit(5).execute()
    
    trends = supabase.table("gold_monthly_trends").select("*").execute()
    
    flagged_summary = supabase.table("gold_flagged_summary").select(
        "*"
    ).execute()
    
    return {
        "top_categories": categories.data,
        "monthly_trends": trends.data,
        "flagged_summary": flagged_summary.data
    }

EXTRACTION_PROMPT = """You are the Extraction Agent for FinSight Enterprise AI.

You have been given financial data from the database.
Your job is to:
1. Identify the most relevant data for the query
2. Summarize what you found
3. Flag anything that needs deeper analysis

Respond with a JSON object:
{
    "data_summary": "brief summary of what data you found",
    "key_findings": ["finding 1", "finding 2"],
    "anomalies_found": ["anomaly 1", "anomaly 2"],
    "recommended_focus": "what the analysis agent should focus on"
}
"""

def extraction_agent_node(state: FinSightState) -> FinSightState:
    """
    Fetches relevant data based on the supervisor's intent
    and prepares it for the Analysis Agent.
    """
    llm = get_llm()
    intent = state.get("extracted_data", {}).get("intent", "full_analysis")
    
    print(f"\n📊 Extraction Agent running (intent: {intent})")
    
    # Fetch data based on intent
    flagged_only = intent == "check_anomalies"
    transactions_data = fetch_transactions(flagged_only=flagged_only)
    kpis_data = fetch_kpis()
    
    # Prepare context for LLM
    context = f"""
Query: {state['query']}
Intent: {intent}

Transaction Summary:
- Total transactions: {transactions_data['summary']['total_count']}
- Total credit: AED {transactions_data['summary']['total_credit_aed']:,.2f}
- Total debit: AED {transactions_data['summary']['total_debit_aed']:,.2f}
- Flagged count: {transactions_data['summary']['flagged_count']}

Flagged Transactions:
{json.dumps(transactions_data['flagged_transactions'][:5], indent=2)}

Top Spending Categories:
{json.dumps(kpis_data['top_categories'][:5], indent=2)}
"""
    
    messages = [
        SystemMessage(content=EXTRACTION_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = llm.invoke(messages)
    
    # Parse response
    try:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        extraction_result = json.loads(content[start:end])
    except Exception:
        extraction_result = {
            "data_summary": "Data extracted successfully",
            "key_findings": [],
            "anomalies_found": [],
            "recommended_focus": "Review flagged transactions"
        }
    
    print(f"   Found: {extraction_result.get('data_summary', '')[:80]}")
    
    # Merge all extracted data
    full_extracted = {
        **state.get("extracted_data", {}),
        "transactions": transactions_data,
        "kpis": kpis_data,
        "extraction_summary": extraction_result
    }
    
    return {
        **state,
        "next_agent": "analysis_agent",
        "extracted_data": full_extracted,
        "messages": state["messages"] + [response]
    }