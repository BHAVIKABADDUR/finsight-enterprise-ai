# agents/graph.py
# Wires all agents together into a LangGraph graph
# LangSmith tracing enabled for every run

import os
import uuid
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from agents.state import FinSightState
from agents.supervisor import supervisor_node
from agents.extraction_agent import extraction_agent_node
from agents.analysis_agent import analysis_agent_node
from agents.decision_agent import decision_agent_node
from agents.audit_agent import audit_agent_node

load_dotenv()

# ── LangSmith tracing setup ───────────────────────────────────────────────────
# These environment variables activate tracing automatically
# Every LLM call will be recorded in LangSmith dashboard
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_PROJECT"] = os.getenv(
    "LANGCHAIN_PROJECT", "finsight-enterprise-ai"
)
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")

from langsmith import Client
from langsmith import traceable

# ── Build the graph ───────────────────────────────────────────────────────────
def build_graph():
    """
    Builds and compiles the LangGraph agent graph.
    LangSmith automatically traces every LLM call inside each node.
    
    Graph structure:
    START → supervisor → extraction → analysis → decision → audit → END
    """
    graph = StateGraph(FinSightState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("extraction_agent", extraction_agent_node)
    graph.add_node("analysis_agent", analysis_agent_node)
    graph.add_node("decision_agent", decision_agent_node)
    graph.add_node("audit_agent", audit_agent_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "extraction_agent")
    graph.add_edge("extraction_agent", "analysis_agent")
    graph.add_edge("analysis_agent", "decision_agent")
    graph.add_edge("decision_agent", "audit_agent")
    graph.add_edge("audit_agent", END)

    return graph.compile()

# ── Run with LangSmith tracing ────────────────────────────────────────────────
@traceable(
    name="FinSight Full Analysis",
    tags=["finsight", "financial-ai", "multi-agent"]
)
def run_analysis(query: str) -> dict:
    """
    Run a complete financial analysis using the agent graph.
    
    @traceable decorator means LangSmith records:
    - The full run as a single trace
    - Every LLM call inside as child spans
    - Token counts and latency per span
    - Input query and final output
    
    Args:
        query: Natural language question about the financial data
        
    Returns:
        Final state containing all agent outputs
    """
    graph = build_graph()
    run_id = str(uuid.uuid4())

    initial_state = {
        "query": query,
        "run_id": run_id,
        "messages": [],
        "next_agent": None,
        "extracted_data": None,
        "analysis_results": None,
        "final_decision": None,
        "audit_complete": False,
        "errors": []
    }

    print(f"\n{'='*60}")
    print(f"🚀 Starting FinSight Analysis")
    print(f"   Query: {query}")
    print(f"   Run ID: {run_id}")
    print(f"   LangSmith Project: {os.getenv('LANGCHAIN_PROJECT')}")
    print(f"{'='*60}")

    final_state = graph.invoke(initial_state)

    print(f"\n{'='*60}")
    print(f"✅ Analysis Complete")
    print(f"   View trace at: https://smith.langchain.com")
    print(f"{'='*60}")

    return final_state

# ── Verify LangSmith connection ───────────────────────────────────────────────
def verify_langsmith():
    """Check LangSmith is connected and project exists."""
    try:
        client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))
        projects = list(client.list_projects())
        project_names = [p.name for p in projects]

        if "finsight-enterprise-ai" in project_names:
            print("✅ LangSmith connected — project found")
        else:
            print("✅ LangSmith connected — project will be created on first run")

        return True
    except Exception as e:
        print(f"⚠️  LangSmith connection issue: {e}")
        return False

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Verify LangSmith first
    verify_langsmith()

    # Run analysis
    result = run_analysis(
        "Analyse our financial transactions and identify "
        "any suspicious activity or anomalies that need review."
    )

    decision = result.get("final_decision", {})
    print(f"\n── Final Decision ──")
    print(f"Risk Rating: {decision.get('overall_risk_rating', 'N/A')}")
    print(f"Requires Human Review: {decision.get('requires_human_review', False)}")
    print(f"\nExecutive Summary:")
    print(f"{decision.get('executive_summary', 'N/A')}")

    print(f"\nRecommended Actions:")
    for action in decision.get("recommended_actions", []):
        print(f"  [{action.get('priority', '').upper()}] {action.get('action', '')}")

    print(f"\n🔍 View full trace at: https://smith.langchain.com")
    print(f"   Project: finsight-enterprise-ai")