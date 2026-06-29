# llmops/cost_tracker.py
# Tracks token costs and latency per agent run
# Stores metrics in Supabase for the observability dashboard

import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from loguru import logger

load_dotenv()

# ── Groq pricing (per 1M tokens) ─────────────────────────────────────────────
# As of June 2026 — free tier has no cost but we track usage
GROQ_PRICING = {
    "llama-3.3-70b-versatile": {
        "input": 0.59,   # USD per 1M input tokens
        "output": 0.79   # USD per 1M output tokens
    }
}

def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """Calculate cost in USD for a model call."""
    pricing = GROQ_PRICING.get(model, {"input": 0.59, "output": 0.79})
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

def update_run_metrics(
    run_id: str,
    agent_name: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    model: str = "llama-3.3-70b-versatile"
):
    """
    Update run metrics for a specific agent call.
    Called after every LLM invocation.
    """
    supabase = get_supabase()
    cost = calculate_cost(model, input_tokens, output_tokens)
    total_tokens = input_tokens + output_tokens

    # Check if run_metrics record exists
    existing = supabase.table("run_metrics").select("*").eq(
        "run_id", run_id
    ).execute()

    if existing.data:
        # Update existing record
        current = existing.data[0]
        supabase.table("run_metrics").update({
            "total_tokens": current["total_tokens"] + total_tokens,
            "total_cost_usd": float(current["total_cost_usd"]) + cost,
            "latency_ms": max(current.get("latency_ms") or 0, latency_ms)
        }).eq("run_id", run_id).execute()
    else:
        # Create new record
        supabase.table("run_metrics").insert({
            "run_id": run_id,
            "total_tokens": total_tokens,
            "total_cost_usd": cost,
            "latency_ms": latency_ms,
            "agents_involved": [agent_name],
            "status": "running"
        }).execute()

    logger.info(
        f"Metrics updated — Run: {run_id[:8]}... | "
        f"Agent: {agent_name} | "
        f"Tokens: {total_tokens} | "
        f"Cost: ${cost:.6f}"
    )

def get_run_metrics(run_id: str) -> dict:
    """Get metrics for a specific run."""
    supabase = get_supabase()
    result = supabase.table("run_metrics").select("*").eq(
        "run_id", run_id
    ).execute()
    return result.data[0] if result.data else {}

def get_all_metrics_summary() -> dict:
    """Get summary of all runs for the dashboard."""
    supabase = get_supabase()
    result = supabase.table("run_metrics").select("*").execute()
    metrics = result.data

    if not metrics:
        return {
            "total_runs": 0,
            "total_tokens": 0,
            "total_cost_usd": 0,
            "avg_latency_ms": 0
        }

    total_tokens = sum(m.get("total_tokens", 0) or 0 for m in metrics)
    total_cost = sum(float(m.get("total_cost_usd", 0) or 0) for m in metrics)
    latencies = [m.get("latency_ms", 0) or 0 for m in metrics if m.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    return {
        "total_runs": len(metrics),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "avg_latency_ms": round(avg_latency, 0)
    }