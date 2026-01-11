from typing import TypedDict, List, Literal, Optional, Dict, Any
from amnesic.presets.code_agent import FrameworkState, Artifact

class DecisionTrace(TypedDict):
    step: int
    tool_call: str
    rationale: str
    auditor_verdict: str
    confidence_score: float

class AgentState(TypedDict):
    # The "Save File" - Strict Pydantic Model
    framework_state: FrameworkState
    
    # The Fluid Context (L1 Cache)
    active_file_map: dict
    current_context_window: str
    
    # History & Metadata
    decision_history: List[DecisionTrace]
    global_uncertainty: float
    last_error: Optional[str]
    chat_history: List[dict]
    
    # Transient State
    manager_decision: Dict[str, Any]
    last_drift_score: float
    pager: Any