# agents/state.py
# Defines the shared state that flows through the entire agent graph
# Every agent reads from and writes to this state

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages

class FinSightState(TypedDict):
    """
    The shared state object that flows through all agents.
    
    Think of this as the "briefcase" that gets passed from
    agent to agent. Each agent adds their findings to it.
    
    TypedDict means every key has a defined type —
    this prevents bugs where an agent writes the wrong type.
    """
    
    # The original user query
    query: str
    
    # Unique ID for this analysis run (used for audit logging)
    run_id: str
    
    # Conversation messages (add_messages handles appending correctly)
    messages: Annotated[list, add_messages]
    
    # Which agent should handle the next step
    next_agent: Optional[str]
    
    # Raw data pulled by the Extraction Agent
    extracted_data: Optional[dict]
    
    # Analysis findings from the Analysis Agent
    analysis_results: Optional[dict]
    
    # Final decision from the Decision Agent
    final_decision: Optional[dict]
    
    # Whether this run has been fully audited
    audit_complete: bool
    
    # Any errors that occurred during the run
    errors: List[str]