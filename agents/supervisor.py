# agents/supervisor.py
# The Supervisor agent — routes queries to the right agents
# Acts as the orchestrator of the entire system

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import FinSightState

load_dotenv()

# ── LLM setup ─────────────────────────────────────────────────────────────────
def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )

# ── Supervisor system prompt ──────────────────────────────────────────────────
SUPERVISOR_PROMPT = """You are the Supervisor of FinSight Enterprise AI, 
a financial document intelligence system.

Your job is to analyse the user's query and decide what needs to be done.

You always respond with a JSON object in this exact format:
{
    "intent": "one of: analyse_transactions, check_anomalies, get_summary, full_analysis",
    "next_agent": "extraction_agent",
    "reasoning": "why you chose this intent",
    "focus_areas": ["list", "of", "things", "to", "focus", "on"]
}

Intent definitions:
- analyse_transactions: User wants to understand transaction patterns
- check_anomalies: User wants to find suspicious or flagged transactions  
- get_summary: User wants a high-level overview
- full_analysis: User wants a complete deep-dive analysis

Always set next_agent to "extraction_agent" — it always goes there first.
"""

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
    
    # Parse the JSON response
    import json
    try:
        # Extract JSON from response
        content = response.content
        # Find JSON block in response
        start = content.find("{")
        end = content.rfind("}") + 1
        json_str = content[start:end]
        decision = json.loads(json_str)
    except Exception as e:
        # Fallback if JSON parsing fails
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