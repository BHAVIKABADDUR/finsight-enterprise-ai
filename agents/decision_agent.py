# agents/decision_agent.py
# Makes final risk decisions with clear reasoning
# This is the last AI agent before human review

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
        temperature=0
    )

DECISION_PROMPT = """FinSight Decision Agent. Return ONLY JSON: {"overall_risk_rating":"MEDIUM","confidence":0.8,"primary_concerns":[""],"recommended_actions":[{"action":"","priority":"immediate","reason":""}],"requires_human_review":true,"human_review_reason":"","executive_summary":"","decision_reasoning":""}"""

def decision_agent_node(state: FinSightState) -> FinSightState:
    """
    Makes final risk decisions based on analysis findings.
    Determines if human review is required.
    """
    llm = get_llm()
    analysis = state.get("analysis_results", {})
    extracted = state.get("extracted_data", {})

    print(f"\n⚖️  Decision Agent running...")

    context = f"""
Original Query: {state['query']}

Analysis Results:
{json.dumps(analysis, indent=2, default=str)}

Transaction Summary:
{json.dumps(extracted.get('transactions', {}).get('summary', {}), indent=2)}

Make a final decision on the risk level and required actions.
"""

    messages = [
        SystemMessage(content=DECISION_PROMPT),
        HumanMessage(content=context)
    ]

    response = llm.invoke(messages)

    try:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        decision = json.loads(content[start:end])
    except Exception:
        decision = {
            "overall_risk_rating": "MEDIUM",
            "confidence": 0.7,
            "primary_concerns": ["Unable to fully parse analysis"],
            "recommended_actions": [
                {
                    "action": "Manual review recommended",
                    "priority": "soon",
                    "reason": "Automated decision incomplete"
                }
            ],
            "requires_human_review": True,
            "human_review_reason": "Automated decision incomplete",
            "executive_summary": "Analysis completed. Manual review recommended.",
            "decision_reasoning": "Default decision due to parsing error"
        }

    risk = decision.get("overall_risk_rating", "MEDIUM")
    requires_review = decision.get("requires_human_review", False)

    print(f"   Risk rating: {risk}")
    print(f"   Requires human review: {requires_review}")
    print(f"   Summary: {decision.get('executive_summary', '')[:80]}")

    return {
        **state,
        "next_agent": "audit_agent",
        "final_decision": decision,
        "messages": state["messages"] + [response]
    }
