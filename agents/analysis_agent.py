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

# ── Load Streamlit secrets into env on cloud ──────────────────────────────────
try:
    import streamlit as st
    for key, value in st.secrets.items():
        os.environ[key] = str(value)
except Exception:
    pass

def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    return ChatGroq(
        model="compound-beta",
        api_key=api_key,
        temperature=0, max_tokens=500
    )

ANALYSIS_PROMPT = """FinSight Analysis Agent. Return ONLY JSON: {"spending_analysis":{"highest_category":"","spending_pattern":""},"anomaly_assessment":{"total_flagged":0,"risk_level":"medium","most_serious":""},"trends":{"observation":"","concern":""},"key_risks":[""],"analysis_summary":""}"""

def analysis_agent_node(state: FinSightState) -> FinSightState:
    """
    Performs deep analysis on extracted data.
    Identifies patterns, risks and anomaly severity.
    """
    llm = get_llm()
    extracted = state.get("extracted_data", {})

    print(f"\n🔍 Analysis Agent running...")

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
{json.dumps(flagged[:3], default=str)[:300]}

Top Spending Categories:
{json.dumps(top_categories[:3], default=str)[:200]}

Monthly Trends:
{json.dumps(monthly_trends[:3], default=str)[:200]}
"""

    messages = [
        SystemMessage(content=ANALYSIS_PROMPT),
        HumanMessage(content=context)
    ]

    response = llm.invoke(messages)

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
