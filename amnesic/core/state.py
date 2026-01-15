from typing import TypedDict, List, Optional, Dict, Any
from amnesic.presets.code_agent import FrameworkState, ManagerMove

class AgentState(TypedDict):
    """
    The Single Source of Truth for the LangGraph state.
    """
    framework_state: FrameworkState
    active_file_map: List[Dict[str, Any]]
    manager_decision: Optional[ManagerMove]
    last_audit: Optional[dict] 
    tool_output: Optional[str]
    last_node: Optional[str]
