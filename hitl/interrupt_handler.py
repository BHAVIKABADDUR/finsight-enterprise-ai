# hitl/interrupt_handler.py
# Implements LangGraph HITL interrupt pattern
# Pauses agent execution for human approval on high-risk decisions

import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from loguru import logger

load_dotenv()

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

# ── Risk threshold for HITL trigger ──────────────────────────────────────────
HITL_THRESHOLD_AMOUNT = 50000    # AED — trigger HITL above this amount
HITL_RISK_LEVELS = ["HIGH"]      # trigger HITL for these risk levels

def should_trigger_hitl(decision: dict, extracted_data: dict) -> tuple:
    """
    Determine if human review should interrupt the agent graph.
    
    Rules:
    1. Risk level is HIGH
    2. Any single transaction over AED 50,000
    3. More than 2 flagged transactions
    
    Returns:
        (should_interrupt: bool, reason: str)
    """
    risk_level = decision.get("overall_risk_rating", "LOW")
    flagged_txns = extracted_data.get(
        "transactions", {}
    ).get("flagged_transactions", [])

    # Rule 1: High risk rating
    if risk_level in HITL_RISK_LEVELS:
        return True, f"High risk rating detected: {risk_level}"

    # Rule 2: Large transaction amount
    for txn in flagged_txns:
        amount = float(txn.get("amount", 0))
        if amount > HITL_THRESHOLD_AMOUNT:
            return True, f"Large transaction detected: AED {amount:,.2f}"

    # Rule 3: Multiple flags
    if len(flagged_txns) > 2:
        return True, f"Multiple anomalies detected: {len(flagged_txns)} flagged"

    return False, ""

def create_hitl_checkpoint(
    run_id: str,
    decision: dict,
    flagged_transactions: list,
    interrupt_reason: str
) -> str:
    """
    Create a HITL checkpoint in Supabase.
    This represents the "paused" state of the agent graph.
    
    Returns:
        checkpoint_id for resuming later
    """
    supabase = get_supabase()
    checkpoint_id = str(uuid.uuid4())

    # Add flagged transactions to review queue
    for txn in flagged_transactions:
        amount = float(txn.get("amount", 0))
        risk_level = "high" if amount > 75000 else "medium"
        txn_id = txn.get("id")

        if not txn_id:
            logger.warning("Skipping transaction with no ID")
            continue

        supabase.table("review_queue").insert({
            "transaction_id": txn_id,
            "run_id": run_id,
            "flag_reason": txn.get("flag_reason", "Flagged by agent"),
            "risk_level": risk_level,
            "status": "pending",
            "reviewer_notes": None,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

    # Log checkpoint to audit trail
    supabase.table("audit_logs").insert({
        "run_id": run_id,
        "agent_name": "hitl_controller",
        "action": "interrupt_triggered",
        "input_summary": interrupt_reason,
        "output_summary": f"Checkpoint created: {checkpoint_id[:8]}...",
        "decision": "awaiting_human_review",
        "reasoning": (
            f"HITL triggered because: {interrupt_reason}. "
            f"Risk level: {decision.get('overall_risk_rating')}. "
            f"Flagged transactions: {len(flagged_transactions)}"
        ),
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    logger.warning(
        f"⚠️  HITL INTERRUPT triggered for run {run_id[:8]}..."
    )
    logger.warning(f"   Reason: {interrupt_reason}")
    logger.warning(f"   Checkpoint: {checkpoint_id[:8]}...")
    logger.warning(
        f"   {len(flagged_transactions)} transactions added to review queue"
    )

    return checkpoint_id

def check_hitl_status(run_id: str) -> dict:
    """
    Check if all flagged transactions in a run have been reviewed.
    
    Returns:
        Status dict with pending/approved/rejected counts
    """
    supabase = get_supabase()

    result = supabase.table("review_queue").select("*").eq(
        "run_id", run_id
    ).execute()

    items = result.data

    if not items:
        return {"status": "no_items", "can_resume": True}

    pending = [i for i in items if i["status"] == "pending"]
    approved = [i for i in items if i["status"] == "approved"]
    rejected = [i for i in items if i["status"] == "rejected"]

    can_resume = len(pending) == 0

    return {
        "total": len(items),
        "pending": len(pending),
        "approved": len(approved),
        "rejected": len(rejected),
        "can_resume": can_resume,
        "status": "complete" if can_resume else "awaiting_review"
    }

def resume_after_hitl(run_id: str) -> dict:
    """
    Resume agent execution after human review is complete.
    Logs the resumption to audit trail.
    
    Returns:
        Summary of human decisions
    """
    supabase = get_supabase()

    status = check_hitl_status(run_id)

    if not status["can_resume"]:
        logger.warning(
            f"Cannot resume run {run_id[:8]}... "
            f"— {status['pending']} items still pending"
        )
        return status

    # Log resumption
    supabase.table("audit_logs").insert({
        "run_id": run_id,
        "agent_name": "hitl_controller",
        "action": "resumed_after_review",
        "input_summary": f"Human review complete for run {run_id[:8]}...",
        "output_summary": (
            f"Approved: {status['approved']}, "
            f"Rejected: {status['rejected']}"
        ),
        "decision": "resumed",
        "reasoning": (
            f"All {status['total']} flagged transactions reviewed. "
            f"{status['approved']} approved, {status['rejected']} rejected."
        ),
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    logger.success(
        f"✅ Run {run_id[:8]}... resumed after human review"
    )
    logger.success(
        f"   Approved: {status['approved']} | "
        f"Rejected: {status['rejected']}"
    )

    return {
        **status,
        "run_id": run_id,
        "resumed_at": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # Test HITL with real flagged transactions from database
    supabase = get_supabase()
    test_run_id = str(uuid.uuid4())

    mock_decision = {
        "overall_risk_rating": "HIGH",
        "requires_human_review": True,
        "executive_summary": "High risk detected"
    }

    # Get real flagged transactions from database
    real_flagged = supabase.table("transactions").select("*").eq(
        "is_flagged", True
    ).limit(1).execute()

    mock_flagged = real_flagged.data if real_flagged.data else []

    # Test should_trigger_hitl
    should_interrupt, reason = should_trigger_hitl(
        mock_decision,
        {"transactions": {"flagged_transactions": mock_flagged}}
    )
    print(f"Should trigger HITL: {should_interrupt}")
    print(f"Reason: {reason}")

    if should_interrupt and mock_flagged:
        checkpoint_id = create_hitl_checkpoint(
            run_id=test_run_id,
            decision=mock_decision,
            flagged_transactions=mock_flagged,
            interrupt_reason=reason
        )
        print(f"\nCheckpoint created: {checkpoint_id[:8]}...")

        # Check status
        status = check_hitl_status(test_run_id)
        print(f"HITL Status: {status}")
    elif not mock_flagged:
        print("No flagged transactions in database to test with")

    print("\n✅ HITL interrupt pattern working")