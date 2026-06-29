# agents/audit_agent.py
# Logs all agent decisions to the audit trail
# Final step in every agent run

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from agents.state import FinSightState

load_dotenv()

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

def audit_agent_node(state: FinSightState) -> FinSightState:
    """
    Logs all agent decisions to the audit trail in Supabase.
    This provides the governance layer for the entire system.
    """
    supabase = get_supabase()
    run_id = state["run_id"]
    
    print(f"\n📝 Audit Agent logging run: {run_id}")
    
    analysis = state.get("analysis_results", {})
    decision = state.get("final_decision", {})
    extracted = state.get("extracted_data", {})
    
    # Build audit entries for each agent
    audit_entries = [
        {
            "run_id": run_id,
            "agent_name": "supervisor",
            "action": "query_routing",
            "input_summary": state.get("query", ""),
            "output_summary": f"Routed to extraction with intent: {extracted.get('intent', 'unknown')}",
            "decision": extracted.get("intent", "full_analysis"),
            "reasoning": extracted.get("supervisor_reasoning", ""),
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "run_id": run_id,
            "agent_name": "extraction_agent",
            "action": "data_extraction",
            "input_summary": f"Intent: {extracted.get('intent', 'unknown')}",
            "output_summary": extracted.get(
                "extraction_summary", {}
            ).get("data_summary", ""),
            "decision": "extracted_successfully",
            "reasoning": str(
                extracted.get("extraction_summary", {}).get("key_findings", [])
            ),
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "run_id": run_id,
            "agent_name": "analysis_agent",
            "action": "pattern_analysis",
            "input_summary": "Extracted transaction and KPI data",
            "output_summary": analysis.get("analysis_summary", ""),
            "decision": analysis.get(
                "anomaly_assessment", {}
            ).get("risk_level", "unknown"),
            "reasoning": str(analysis.get("key_risks", [])),
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "run_id": run_id,
            "agent_name": "decision_agent",
            "action": "risk_decision",
            "input_summary": "Analysis findings",
            "output_summary": decision.get("executive_summary", ""),
            "decision": decision.get("overall_risk_rating", "UNKNOWN"),
            "reasoning": decision.get("decision_reasoning", ""),
            "created_at": datetime.utcnow().isoformat()
        }
    ]
    
    # Write all audit entries to Supabase
    supabase.table("audit_logs").insert(audit_entries).execute()
    
    # Write run metrics
    run_metrics = {
        "run_id": run_id,
        "total_tokens": len(state.get("messages", [])) * 500,  # estimate
        "total_cost_usd": len(state.get("messages", [])) * 0.0002,
        "agents_involved": [
            "supervisor",
            "extraction_agent",
            "analysis_agent",
            "decision_agent",
            "audit_agent"
        ],
        "documents_processed": 3,
        "transactions_extracted": extracted.get(
            "transactions", {}
        ).get("summary", {}).get("total_count", 0),
        "flags_raised": extracted.get(
            "transactions", {}
        ).get("summary", {}).get("flagged_count", 0),
        "status": "completed",
        "created_at": datetime.utcnow().isoformat()
    }
    
    supabase.table("run_metrics").insert(run_metrics).execute()
    
    print(f"   ✅ Logged {len(audit_entries)} audit entries")
    print(f"   ✅ Run metrics recorded")
    
    return {
        **state,
        "next_agent": None,
        "audit_complete": True
    }