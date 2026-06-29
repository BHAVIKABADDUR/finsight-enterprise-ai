# agents/graph.py
# Wires all agents together into a LangGraph graph
# This is the orchestration layer

import uuid
from langgraph.graph import StateGraph, END
from agents.state import FinSightState
from agents.supervisor import supervisor_node
from agents.extraction_agent import extraction_agent_node
from agents.analysis_agent import analysis_agent_node
from agents.decision_agent import decision_agent_node
from agents.audit_agent import audit_agent_node

# ── Build the graph ───────────────────────────────────────────────────────────
def build_graph():
    """
    Builds and compiles the LangGraph agent graph.
    
    Graph structure:
    START → supervisor → extraction → analysis → decision → audit → END
    """
    
    # Create the graph with our state definition
    graph = StateGraph(FinSightState)
    
    # Add all agent nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("extraction_agent", extraction_agent_node)
    graph.add_node("analysis_agent", analysis_agent_node)
    graph.add_node("decision_agent", decision_agent_node)
    graph.add_node("audit_agent", audit_agent_node)
    
    # Define the edges (flow between agents)
    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "extraction_agent")
    graph.add_edge("extraction_agent", "analysis_agent")
    graph.add_edge("analysis_agent", "decision_agent")
    graph.add_edge("decision_agent", "audit_agent")
    graph.add_edge("audit_agent", END)
    
    # Compile the graph
    return graph.compile()

# ── Run the graph ─────────────────────────────────────────────────────────────
def run_analysis(query: str) -> dict:
    """
    Run a complete financial analysis using the agent graph.
    
    Args:
        query: Natural language question about the financial data
        
    Returns:
        Final state containing all agent outputs
    """
    graph = build_graph()
    run_id = str(uuid.uuid4())
    
    # Initial state
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
    print(f"{'='*60}")
    
    # Run the graph
    final_state = graph.invoke(initial_state)
    
    print(f"\n{'='*60}")
    print(f"✅ Analysis Complete")
    print(f"{'='*60}")
    
    return final_state

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Test with a sample query
    result = run_analysis(
        "Analyse our financial transactions and identify any suspicious activity or anomalies that need review."
    )
    
    # Print final decision
    decision = result.get("final_decision", {})
    print(f"\n── Final Decision ──")
    print(f"Risk Rating: {decision.get('overall_risk_rating', 'N/A')}")
    print(f"Requires Human Review: {decision.get('requires_human_review', False)}")
    print(f"\nExecutive Summary:")
    print(f"{decision.get('executive_summary', 'N/A')}")
    
    print(f"\nRecommended Actions:")
    for action in decision.get("recommended_actions", []):
        print(f"  [{action.get('priority', '').upper()}] {action.get('action', '')}")
    
    print(f"\nAudit complete: {result.get('audit_complete', False)}")