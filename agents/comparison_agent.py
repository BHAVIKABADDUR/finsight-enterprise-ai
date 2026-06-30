# agents/comparison_agent.py
# Multi-document comparison agent
# Compares trends across multiple time periods / documents

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

COMPARISON_PROMPT = """You are a financial trend comparison specialist for FinSight Enterprise AI.

You will be given transaction data grouped by month. Your job is to compare 
periods and identify meaningful changes.

Return ONLY a JSON object with this structure:
{
    "trend_summary": "2-3 sentence overview of the overall trend across periods",
    "period_comparisons": [
        {
            "period": "month name",
            "total_spend": 0.00,
            "change_from_previous": "increased/decreased/stable",
            "change_percentage": 0.0,
            "notable_change": "what stands out about this period"
        }
    ],
    "category_shifts": [
        {
            "category": "category name",
            "trend": "increasing/decreasing/stable",
            "observation": "what changed and why it might matter"
        }
    ],
    "risk_trajectory": "improving/worsening/stable",
    "key_insight": "the single most important thing a business stakeholder should know",
    "recommendation": "one specific recommendation based on the comparison"
}

Rules:
- Base everything on the actual numbers provided
- Be specific with percentages and amounts where possible
- Focus on changes that matter for risk and business decisions
"""

def get_monthly_breakdown() -> dict:
    """
    Pull monthly transaction data from Gold layer for comparison.
    """
    supabase = get_supabase()

    result = supabase.table("gold_monthly_trends").select("*").execute()
    monthly_data = result.data

    # Get category breakdown per month by querying transactions directly
    txn_result = supabase.table("transactions").select(
        "transaction_date, category, amount, transaction_type, is_flagged"
    ).execute()
    transactions = txn_result.data

    # Group by month + category
    monthly_categories = {}
    for txn in transactions:
        date_str = txn.get("transaction_date", "")
        if not date_str:
            continue
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = date.strftime("%B %Y")
        except ValueError:
            continue

        if month_key not in monthly_categories:
            monthly_categories[month_key] = {}

        category = txn.get("category", "Unknown")
        amount = float(txn.get("amount", 0))

        if category not in monthly_categories[month_key]:
            monthly_categories[month_key][category] = 0
        monthly_categories[month_key][category] += amount

    return {
        "monthly_trends": monthly_data,
        "monthly_categories": monthly_categories
    }

def compare_periods(focus_area: str = "all spending patterns") -> dict:
    """
    Run a full multi-period comparison analysis.
    
    Args:
        focus_area: What aspect to focus the comparison on
        
    Returns:
        Comparison analysis results
    """
    client = get_groq()
    data = get_monthly_breakdown()

    logger.info(f"Comparing periods with focus: {focus_area}")

    context = f"""
Focus area: {focus_area}

Monthly Trends (from Gold layer):
{json.dumps(data['monthly_trends'], indent=2, default=str)}

Monthly Category Breakdown:
{json.dumps(data['monthly_categories'], indent=2, default=str)}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": COMPARISON_PROMPT},
            {"role": "user", "content": context}
        ],
        temperature=0,
        max_tokens=1500
    )

    content = response.choices[0].message.content

    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        comparison = json.loads(content[start:end])
    except Exception as e:
        logger.error(f"Failed to parse comparison: {e}")
        comparison = {
            "trend_summary": "Comparison could not be completed",
            "period_comparisons": [],
            "category_shifts": [],
            "risk_trajectory": "unknown",
            "key_insight": "Insufficient data for comparison",
            "recommendation": "Gather more historical data"
        }

    logger.success(f"Comparison complete: {comparison.get('trend_summary', '')[:80]}")

    return {
        "raw_data": data,
        "comparison": comparison,
        "tokens_used": response.usage.total_tokens
    }

if __name__ == "__main__":
    result = compare_periods("spending patterns and risk trends across all months")

    comparison = result["comparison"]

    print(f"\n{'='*60}")
    print("MULTI-PERIOD COMPARISON ANALYSIS")
    print('='*60)

    print(f"\nTrend Summary:\n{comparison.get('trend_summary', '')}")

    print(f"\nRisk Trajectory: {comparison.get('risk_trajectory', '').upper()}")

    print(f"\nPeriod Comparisons:")
    for p in comparison.get("period_comparisons", []):
        spend = p.get("total_spend", 0)
        try:
            spend = float(spend)
        except (ValueError, TypeError):
            spend = 0.0

        change_pct = p.get("change_percentage", 0)
        try:
            change_pct = float(change_pct)
        except (ValueError, TypeError):
            change_pct = 0.0

        print(
            f"  {p.get('period')}: AED {spend:,.2f} "
            f"({p.get('change_from_previous', '')}, "
            f"{change_pct:+.1f}%)"
        )
        print(f"    → {p.get('notable_change', '')}")

    print(f"\nCategory Shifts:")
    for c in comparison.get("category_shifts", []):
        print(f"  {c.get('category')}: {c.get('trend', '').upper()}")
        print(f"    → {c.get('observation', '')}")

    print(f"\nKey Insight:\n{comparison.get('key_insight', '')}")
    print(f"\nRecommendation:\n{comparison.get('recommendation', '')}")

    print(f"\nTokens used: {result['tokens_used']}")