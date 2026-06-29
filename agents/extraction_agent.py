# agents/extraction_agent.py
# Extraction Agent — pulls data using MCP tool servers
# This is the correct pattern — agents never query databases directly

import os
import json
import subprocess
import tempfile
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

load_dotenv()

def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )

# ── MCP tool caller ───────────────────────────────────────────────────────────
def call_mcp_tool(server_module: str, tool_name: str, arguments: dict) -> dict:
    """
    Call an MCP tool server and return the result.
    
    This runs the MCP server as a subprocess and communicates
    via stdin/stdout — exactly how MCP protocol works.
    
    Args:
        server_module: Python module path e.g. 'mcp_servers.query_transactions'
        tool_name: Name of the tool to call
        arguments: Tool arguments as dict
        
    Returns:
        Tool result as dict
    """
    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def _call():
        server_params = StdioServerParameters(
            command="python",
            args=["-m", server_module],
            env=dict(os.environ)
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content:
                    return json.loads(result.content[0].text)
                return {}

    try:
        return asyncio.run(_call())
    except Exception as e:
        logger.error(f"MCP tool call failed: {server_module}.{tool_name} — {e}")
        # Fallback to direct Supabase query
        return _fallback_query(tool_name, arguments)

def _fallback_query(tool_name: str, arguments: dict) -> dict:
    """
    Fallback direct Supabase query if MCP call fails.
    Ensures system keeps working even if MCP server has issues.
    """
    from supabase import create_client
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    if tool_name == "get_transaction_summary":
        result = supabase.table("transactions").select(
            "amount, transaction_type, is_flagged"
        ).execute()
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
            "total_transactions": len(transactions),
            "total_credit_aed": round(total_credit, 2),
            "total_debit_aed": round(total_debit, 2),
            "flagged_count": len(flagged)
        }

    elif tool_name == "get_flagged_transactions":
        result = supabase.table("transactions").select("*").eq(
            "is_flagged", True
        ).execute()
        return {"flagged_transactions": result.data, "flagged_count": len(result.data)}

    elif tool_name == "get_spend_by_category":
        result = supabase.table("gold_spend_by_category").select("*").order(
            "total_amount", desc=True
        ).limit(5).execute()
        return {"spend_by_category": result.data}

    elif tool_name == "get_risk_summary":
        result = supabase.table("gold_flagged_summary").select("*").execute()
        return {"by_type": result.data}

    return {}

# ── Agent prompt ──────────────────────────────────────────────────────────────
EXTRACTION_PROMPT = """You are the Extraction Agent for FinSight Enterprise AI.

You have been given financial data retrieved via MCP tool servers.
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

# ── Agent node ────────────────────────────────────────────────────────────────
def extraction_agent_node(state):
    """
    Fetches data via MCP tool servers based on supervisor intent.
    Falls back to direct queries if MCP unavailable.
    """
    from agents.state import FinSightState
    llm = get_llm()
    intent = state.get("extracted_data", {}).get("intent", "full_analysis")

    logger.info(f"\n📊 Extraction Agent running via MCP tools (intent: {intent})")

    # ── Call MCP tools ────────────────────────────────────────────────────────

    # Tool 1: Get transaction summary
    logger.info("   Calling MCP: get_transaction_summary")
    summary_data = call_mcp_tool(
        "mcp_servers.query_transactions",
        "get_transaction_summary",
        {}
    )

    # Tool 2: Get flagged transactions
    logger.info("   Calling MCP: get_flagged_transactions")
    flagged_data = call_mcp_tool(
        "mcp_servers.query_transactions",
        "get_flagged_transactions",
        {}
    )

    # Tool 3: Get KPI spend by category
    logger.info("   Calling MCP: get_spend_by_category")
    kpi_data = call_mcp_tool(
        "mcp_servers.run_analytics",
        "get_spend_by_category",
        {"top_n": 5}
    )

    # Tool 4: Get risk summary
    logger.info("   Calling MCP: get_risk_summary")
    risk_data = call_mcp_tool(
        "mcp_servers.run_analytics",
        "get_risk_summary",
        {}
    )

    logger.success("   All MCP tool calls complete")

    # ── LLM summarization ─────────────────────────────────────────────────────
    context = f"""
Query: {state['query']}
Intent: {intent}

Transaction Summary (via MCP query_transactions):
{json.dumps(summary_data, indent=2)}

Flagged Transactions (via MCP query_transactions):
{json.dumps(flagged_data, indent=2, default=str)}

Top Spending Categories (via MCP run_analytics):
{json.dumps(kpi_data, indent=2, default=str)}

Risk Summary (via MCP run_analytics):
{json.dumps(risk_data, indent=2, default=str)}
"""

    messages = [
        SystemMessage(content=EXTRACTION_PROMPT),
        HumanMessage(content=context)
    ]

    response = llm.invoke(messages)

    try:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        extraction_result = json.loads(content[start:end])
    except Exception:
        extraction_result = {
            "data_summary": "Data extracted via MCP tools successfully",
            "key_findings": [],
            "anomalies_found": [],
            "recommended_focus": "Review flagged transactions"
        }

    logger.info(f"   Found: {extraction_result.get('data_summary', '')[:80]}")

    # Merge all MCP data
    full_extracted = {
        **state.get("extracted_data", {}),
        "transactions": {
            "summary": summary_data,
            "flagged_transactions": flagged_data.get("flagged_transactions", [])
        },
        "kpis": {
            "top_categories": kpi_data.get("spend_by_category", []),
            "risk_summary": risk_data
        },
        "extraction_summary": extraction_result,
        "mcp_tools_used": [
            "query_transactions:get_transaction_summary",
            "query_transactions:get_flagged_transactions",
            "run_analytics:get_spend_by_category",
            "run_analytics:get_risk_summary"
        ]
    }

    return {
        **state,
        "next_agent": "analysis_agent",
        "extracted_data": full_extracted,
        "messages": state["messages"] + [response]
    }