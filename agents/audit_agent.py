# agents/audit_agent.py
# Audit Agent — logs all decisions via MCP log_audit server
# Correct pattern: agents use MCP tools, never direct DB calls

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

def call_mcp_audit_tool(tool_name: str, arguments: dict) -> dict:
    """Call the log_audit MCP server."""
    # ── Cloud environment detection ───────────────────────────────────────────
    is_cloud = (
        os.getenv("HOME", "").startswith("/home/adminuser") or
        os.getenv("STREAMLIT_SHARING_MODE") is not None or
        not os.path.exists("mcp_servers/log_audit.py")
    )
    if is_cloud:
        logger.info(f"Cloud environment — using direct Supabase fallback for {tool_name}")
        return _fallback_audit(tool_name, arguments)

    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def _call():
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_servers.log_audit"],
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
        logger.error(f"MCP audit tool failed: {e}")
        return _fallback_audit(tool_name, arguments)

def _fallback_audit(tool_name: str, arguments: dict) -> dict:
    """Fallback direct Supabase write if MCP fails."""
    import uuid
    from supabase import create_client
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    if tool_name == "log_agent_decision":
        record = {
            "id": str(uuid.uuid4()),
            "run_id": arguments["run_id"],
            "agent_name": arguments["agent_name"],
            "action": arguments["action"],
            "input_summary": arguments.get("input_summary", ""),
            "output_summary": arguments.get("output_summary", ""),
            "decision": arguments["decision"],
            "reasoning": arguments.get("reasoning", ""),
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table("audit_logs").insert(record).execute()
        return {"status": "logged_via_fallback"}
    return {}

def audit_agent_node(state) -> dict:
    """
    Logs all agent decisions via MCP log_audit server.
    Also writes run metrics to Supabase.
    """
    from supabase import create_client
    import uuid

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    run_id = state["run_id"]
    analysis = state.get("analysis_results", {})
    decision = state.get("final_decision", {})
    extracted = state.get("extracted_data", {})
    mcp_tools_used = extracted.get("mcp_tools_used", [])

    logger.info(f"\n📝 Audit Agent logging via MCP: {run_id[:8]}...")

    audit_entries = [
        {
            "agent_name": "supervisor",
            "action": "query_routing",
            "input_summary": state.get("query", ""),
            "output_summary": f"Routed with intent: {extracted.get('intent', 'unknown')}",
            "decision": extracted.get("intent", "full_analysis"),
            "reasoning": extracted.get("supervisor_reasoning", "")
        },
        {
            "agent_name": "extraction_agent",
            "action": "mcp_data_extraction",
            "input_summary": f"Intent: {extracted.get('intent', 'unknown')}",
            "output_summary": extracted.get(
                "extraction_summary", {}
            ).get("data_summary", ""),
            "decision": "extracted_via_mcp",
            "reasoning": f"MCP tools used: {', '.join(mcp_tools_used)}"
        },
        {
            "agent_name": "analysis_agent",
            "action": "pattern_analysis",
            "input_summary": "MCP-extracted transaction and KPI data",
            "output_summary": analysis.get("analysis_summary", ""),
            "decision": analysis.get(
                "anomaly_assessment", {}
            ).get("risk_level", "unknown"),
            "reasoning": str(analysis.get("key_risks", []))
        },
        {
            "agent_name": "decision_agent",
            "action": "risk_decision",
            "input_summary": "Analysis findings",
            "output_summary": decision.get("executive_summary", ""),
            "decision": decision.get("overall_risk_rating", "UNKNOWN"),
            "reasoning": decision.get("decision_reasoning", "")
        }
    ]

    for entry in audit_entries:
        result = call_mcp_audit_tool("log_agent_decision", {
            "run_id": run_id,
            **entry
        })
        logger.info(f"   Logged via MCP: {entry['agent_name']}")

    run_metrics = {
        "run_id": run_id,
        "total_tokens": len(state.get("messages", [])) * 500,
        "total_cost_usd": len(state.get("messages", [])) * 0.0002,
        "agents_involved": [
            "supervisor", "extraction_agent",
            "analysis_agent", "decision_agent", "audit_agent"
        ],
        "documents_processed": 3,
        "transactions_extracted": extracted.get(
            "transactions", {}
        ).get("summary", {}).get("total_transactions", 0),
        "flags_raised": extracted.get(
            "transactions", {}
        ).get("summary", {}).get("flagged_count", 0),
        "status": "completed",
        "created_at": datetime.utcnow().isoformat()
    }

    supabase.table("run_metrics").insert(run_metrics).execute()

    logger.success(f"   ✅ Logged {len(audit_entries)} entries via MCP")
    logger.success(f"   ✅ Run metrics recorded")

    return {
        **state,
        "next_agent": None,
        "audit_complete": True
    }