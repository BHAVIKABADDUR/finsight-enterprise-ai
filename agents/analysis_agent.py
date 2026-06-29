# agents/analysis_agent.py
# Analyses patterns, anomalies and trends in extracted data
# Produces structured findings for the Decision Agent

import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import FinSightState

load_dotenv()

def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )

ANALYSIS_PROMPT = """You are the Analysis Agent for FinSight Enterprise AI.

You receive extracted financial data and perform deep analysis.

Your analysis must cover:
1. Spending pattern analysis
2. Anomaly assessment (how serious are the flagged transactions?)
3. Risk identification
4. Trend analysis

Respond with a JSON object:
{
    "spending_analysis": {
        "highest_category": "category name",
        "highest_amount": 0.00,
        "spending_pattern": "description of pattern"
    },
    "anomaly_assessment": {
        "total_flagged": 0,
        "total_flagged_amount_aed": 0.00,
        "most_serious": "description of most serious anomaly",
        "risk_level": "high/medium/low"
    },
    "trends": {
        "observation": "what trends you see",
        "concern": "any concerning trends"
    },
    "key_risks": ["risk 1", "risk 2"],
    "analysis_summary": "2-3 sentence summary of overall findings"
}
"""

def analysis_agent_node(state: FinSightState) -> FinSightState:
    """
    Performs deep analysis on extracted data.
    Identifies patterns, risks and anomaly severity.
    """
    llm = get_llm()
    extracted = state.get("extracted_data", {})
    
    print(f"\n🔍 Analysis Agent running...")
    
    # Build analysis context
    transactions = extracted.get("transactions", {})
    kpis = extracted.get("kpis", {})
    extraction_summary = extracted.get("extraction_summary", {})
    
    flagged = transactions.get("flagged_transactions", [])
    top_categories = kpis.get("top_categories", [])
    monthly_trends = kpis.get("monthly_trends", [])
    
    context = f"""
Query: {state['query']}

Extraction Summary: {extraction_summary.get('data_summary', '')}
Key Findings: {extraction_summary.get('key_findings', [])}
Anomalies Found: {extraction_summary.get('anomalies_found', [])}

Flagged Transactions ({len(flagged)} total):
{json.dumps(flagged, indent=2, default=str)}

Top Spending Categories:
{json.dumps(top_categories, indent=2, default=str)}

Monthly Trends:
{json.dumps(monthly_trends, indent=2, default=str)}
"""
    
    messages = [
        SystemMessage(content=ANALYSIS_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = llm.invoke(messages)
    
    # Parse response
    try:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        analysis_result = json.loads(content[start:end])
    except Exception:
        analysis_result = {
            "spending_analysis": {
                "highest_category": "Unknown",
                "spending_pattern": "Analysis could not be completed"
            },
            "anomaly_assessment": {
                "total_flagged": len(flagged),
                "risk_level": "medium"
            },
            "trends": {"observation": "Insufficient data"},
            "key_risks": [],
            "analysis_summary": "Analysis completed with partial data"
        }
    
    risk_level = analysis_result.get(
        "anomaly_assessment", {}
    ).get("risk_level", "medium")
    print(f"   Risk level: {risk_level}")
    print(f"   Summary: {analysis_result.get('analysis_summary', '')[:80]}")
    
    return {
        **state,
        "next_agent": "decision_agent",
        "analysis_results": analysis_result,
        "messages": state["messages"] + [response]
    }