# llmops/dashboard.py
# LLMOps observability dashboard data
# Feeds the Streamlit audit log page with rich metrics

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
from loguru import logger

load_dotenv()

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

def get_system_health() -> dict:
    """
    Get overall system health metrics.
    Used for the dashboard header cards.
    """
    supabase = get_supabase()

    # Total documents
    docs = supabase.table("documents").select("id, status").execute()
    total_docs = len(docs.data)
    processed_docs = len([d for d in docs.data if d["status"] != "pending"])

    # Total transactions
    txns = supabase.table("transactions").select("id, is_flagged").execute()
    total_txns = len(txns.data)
    flagged_txns = len([t for t in txns.data if t["is_flagged"]])

    # Total runs
    runs = supabase.table("run_metrics").select("*").execute()
    total_runs = len(runs.data)
    total_tokens = sum(r.get("total_tokens", 0) or 0 for r in runs.data)
    total_cost = sum(float(r.get("total_cost_usd", 0) or 0) for r in runs.data)

    # Audit entries
    audit = supabase.table("audit_logs").select("id").execute()
    total_audit_entries = len(audit.data)

    return {
        "total_documents": total_docs,
        "processed_documents": processed_docs,
        "total_transactions": total_txns,
        "flagged_transactions": flagged_txns,
        "total_agent_runs": total_runs,
        "total_tokens_used": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "total_audit_entries": total_audit_entries,
        "system_status": "healthy"
    }

def get_agent_performance() -> list:
    """
    Get performance breakdown per agent.
    Shows which agents are making good decisions.
    """
    supabase = get_supabase()

    result = supabase.table("audit_logs").select(
        "agent_name, action, decision, created_at"
    ).execute()

    logs = result.data

    # Group by agent
    agent_map = {}
    for log in logs:
        agent = log.get("agent_name", "unknown")
        if agent not in agent_map:
            agent_map[agent] = {
                "agent_name": agent,
                "total_calls": 0,
                "actions": []
            }
        agent_map[agent]["total_calls"] += 1
        agent_map[agent]["actions"].append(log.get("action", ""))

    return list(agent_map.values())

if __name__ == "__main__":
    logger.info("Getting system health metrics...")
    health = get_system_health()

    print("\n── System Health ──")
    for key, value in health.items():
        print(f"  {key}: {value}")

    print("\n── Agent Performance ──")
    perf = get_agent_performance()
    for agent in perf:
        print(
            f"  {agent['agent_name']}: "
            f"{agent['total_calls']} calls"
        )