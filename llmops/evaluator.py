# llmops/evaluator.py
# Evaluation pipeline — scores extraction quality and agent decisions
# This is what LLMOps engineers build to ensure system reliability

import os
import json
from datetime import datetime
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

# ── Extraction quality evaluator ──────────────────────────────────────────────
def evaluate_extraction_quality(extraction_result: dict) -> dict:
    """
    Score the quality of an LLM extraction result.
    
    Checks:
    - Field completeness (were all expected fields extracted?)
    - Data validity (are dates valid, amounts positive?)
    - Confidence alignment (does confidence match actual quality?)
    
    Returns:
        Evaluation scores dict
    """
    extracted = extraction_result.get("extracted_fields", {})
    confidence = extraction_result.get("confidence_scores", {}).get("overall", 0)

    scores = {}

    # Score 1: Field completeness
    non_null_fields = sum(
        1 for v in extracted.values()
        if v is not None and v != [] and v != {}
    )
    total_fields = max(len(extracted), 1)
    scores["completeness"] = round(non_null_fields / total_fields, 2)

    # Score 2: Data validity
    validity_checks = []

    # Check amounts are positive
    for key, val in extracted.items():
        if "amount" in key or "balance" in key or "total" in key or "subtotal" in key:
            if isinstance(val, (int, float)):
                validity_checks.append(val > 0)

    # Check transactions if present
    transactions = extracted.get("transactions", [])
    for txn in transactions:
        if isinstance(txn, dict):
            amount = txn.get("amount")
            if amount is not None:
                validity_checks.append(isinstance(amount, (int, float)) and amount >= 0)

    scores["validity"] = round(
        sum(validity_checks) / len(validity_checks), 2
    ) if validity_checks else 0.8

    # Score 3: Overall quality
    scores["overall_quality"] = round(
        (scores["completeness"] + scores["validity"]) / 2, 2
    )

    # Score 4: Confidence calibration
    # How close is the reported confidence to actual quality?
    scores["confidence_calibration"] = round(
        1 - abs(confidence - scores["overall_quality"]), 2
    )

    logger.info(
        f"Extraction evaluation — "
        f"Completeness: {scores['completeness']:.0%} | "
        f"Validity: {scores['validity']:.0%} | "
        f"Quality: {scores['overall_quality']:.0%}"
    )

    return scores

# ── Agent decision evaluator ──────────────────────────────────────────────────
def evaluate_agent_decision(
    query: str,
    decision: dict,
    analysis: dict
) -> dict:
    """
    Use LLM-as-judge to evaluate the quality of an agent decision.
    
    This is a key LLMOps technique — using one LLM to evaluate
    the output of another LLM.
    """
    client = get_groq()

    eval_prompt = """You are an expert financial AI evaluator.
    
Evaluate this AI agent's decision on a scale of 1-10 for each criterion.

Return ONLY a JSON object:
{
    "relevance_score": 0,
    "reasoning_quality": 0,
    "action_specificity": 0,
    "risk_appropriateness": 0,
    "overall_score": 0,
    "feedback": "brief feedback"
}

Scoring criteria:
- relevance_score: Does the decision address the original query? (1-10)
- reasoning_quality: Is the reasoning clear and logical? (1-10)
- action_specificity: Are recommended actions specific and actionable? (1-10)
- risk_appropriateness: Is the risk level appropriate given the evidence? (1-10)
- overall_score: Overall quality of the decision (1-10)
"""

    context = f"""
Original Query: {query}

Agent Decision:
- Risk Rating: {decision.get('overall_risk_rating', 'N/A')}
- Executive Summary: {decision.get('executive_summary', 'N/A')}
- Primary Concerns: {decision.get('primary_concerns', [])}
- Recommended Actions: {decision.get('recommended_actions', [])}

Analysis Results:
- Anomaly Assessment: {analysis.get('anomaly_assessment', {})}
- Analysis Summary: {analysis.get('analysis_summary', 'N/A')}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": eval_prompt},
                {"role": "user", "content": context}
            ],
            temperature=0,
            max_tokens=500
        )

        content = response.choices[0].message.content
        start = content.find("{")
        end = content.rfind("}") + 1
        scores = json.loads(content[start:end])

        logger.success(
            f"Decision evaluation — "
            f"Overall: {scores.get('overall_score', 0)}/10 | "
            f"Feedback: {scores.get('feedback', '')[:60]}"
        )

        return scores

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {
            "relevance_score": 7,
            "reasoning_quality": 7,
            "action_specificity": 7,
            "risk_appropriateness": 7,
            "overall_score": 7,
            "feedback": "Evaluation could not be completed"
        }

# ── Save evaluation to Supabase ───────────────────────────────────────────────
def save_evaluation(run_id: str, eval_type: str, scores: dict):
    """Save evaluation scores to audit_logs for tracking."""
    supabase = get_supabase()

    supabase.table("audit_logs").insert({
        "run_id": run_id,
        "agent_name": "evaluator",
        "action": f"evaluate_{eval_type}",
        "input_summary": f"Evaluation type: {eval_type}",
        "output_summary": json.dumps(scores),
        "decision": f"score_{scores.get('overall_score', scores.get('overall_quality', 0))}",
        "reasoning": scores.get("feedback", str(scores)),
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    logger.success(f"Evaluation saved for run: {run_id}")