# agents/supervisor.py
# The Supervisor agent — routes queries to the right agents
# Acts as the orchestrator of the entire system
import os
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

# ── LLM setup ─────────────────────────────────────────────────────────────────
def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    return ChatGroq(
        model="qwen/qwen3.6-27b",
        api_key=api_key,
        temperature=0,
        max_tokens=200
    )

# ── Supervisor system prompt ──────────────────────────────────────────────────
SUPERVISOR_PROMPT = """FinSight Supervisor. Return ONLY JSON: {"intent":"full_analysis","next_agent":"extraction_agent","reasoning":"","focus_areas":[""]} Intent options: analyse_transactions, check_anomalies, get_summary, full_analysis"""

# ── Supervisor node function ──────────────────────────────────────────────────
def supervisor_node(state: FinSightState) -> FinSightState:
    """
    The Supervisor reads the query and decides what kind of
    analysis is needed. Sets the intent and routes to extraction.
    """
    llm = get_llm()
    query = state["query"]
    
    print(f"\n🎯 Supervisor processing query: {query}")
    
    messages = [
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=f"User query: {query}")
    ]
    
    response = llm.invoke(messages)
    
    import json
    try:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        json_str = content[start:end]
        decision = json.loads(json_str)
    except Exception as e:
        decision = {
            "intent": "full_analysis",
            "next_agent": "extraction_agent",
            "reasoning": "Defaulting to full analysis",
            "focus_areas": ["transactions", "anomalies", "summary"]
        }
    
    print(f"   Intent: {decision.get('intent')}")
    print(f"   Reasoning: {decision.get('reasoning')}")
    
    return {
        **state,
        "next_agent": "extraction_agent",
        "extracted_data": {
            "intent": decision.get("intent"),
            "focus_areas": decision.get("focus_areas", []),
            "supervisor_reasoning": decision.get("reasoning")
        },
        "messages": state["messages"] + [response]
    }
# force redeploy
