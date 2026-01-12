from typing import Callable, Optional
from dataclasses import dataclass
from amnesic.presets.code_agent import FrameworkState, ManagerMove

@dataclass
class KernelPolicy:
    """
    A deterministic rule that overrides the LLM Manager.
    Used for safety rails, mission completion triggers, or forced context wipes.
    """
    name: str
    condition: Callable[[FrameworkState], bool]
    reaction: Callable[[FrameworkState], ManagerMove]
    priority: int = 10  # Higher runs first

# --- Default Policies ---

def _check_mission_complete(state: FrameworkState) -> bool:
    """Checks if completion artifacts exist. 
    Strictly restricted to avoid premature completion in complex missions.
    """
    # Only trigger if the mission explicitly saved a result with identifier "TOTAL"
    # AND we have a verification artifact or it's a simple mission.
    has_total = any(a.identifier == "TOTAL" or "SUCCESS" in a.identifier.upper() for a in state.artifacts)
    has_verification = any(a.identifier == "VERIFICATION" for a in state.artifacts)
    has_violation = any("VIOLATION" in a.identifier.upper() for a in state.artifacts)
    
    # If it's a violation, we can halt immediately.
    if has_violation: return True
    
    # Otherwise, we usually want both a total result and some form of verification
    # or the agent has explicitly stated mission completion in the hypothesis or feedback.
    manager_thinks_complete = "COMPLETE" in state.current_hypothesis.upper() or \
                             (state.last_action_feedback and "COMPLETE" in state.last_action_feedback.upper())
    
    return has_total and (has_verification or manager_thinks_complete)

def _react_mission_complete(state: FrameworkState) -> ManagerMove:
    """Forces a halt when mission is complete."""
    # Find the most relevant completion artifact
    art = next((a for a in state.artifacts if a.identifier == "TOTAL"), None)
    if not art:
        art = next((a for a in state.artifacts if "VIOLATION" in a.identifier.upper()), None)
    if not art:
        art = next((a for a in state.artifacts if a.identifier == "VERIFICATION"), None)
    
    return ManagerMove(
        thought_process=f"The {art.identifier} artifact is present. The mission is complete.",
        tool_call="halt_and_ask",
        target=f"{art.identifier}: {art.summary}"
    )

# The default "Hardcoded" behavior, now essentially a plugin
DEFAULT_COMPLETION_POLICY = KernelPolicy(
    name="LegacyMissionComplete",
    condition=_check_mission_complete,
    reaction=_react_mission_complete
)

def _check_critical_error(state: FrameworkState) -> bool:
    """Checks if the last action resulted in a critical error (e.g. file not found)."""
    # print(f"DEBUG: Checking critical error. Feedback: {state.last_action_feedback}")
    return state.last_action_feedback and "CRITICAL ERROR" in state.last_action_feedback

def _react_critical_error(state: FrameworkState) -> ManagerMove:
    return ManagerMove(
        thought_process=f"A critical error occurred: {state.last_action_feedback}. I must halt immediately.",
        tool_call="halt_and_ask",
        target=state.last_action_feedback
    )

CRITICAL_ERROR_POLICY = KernelPolicy(
    name="CriticalErrorHalt",
    condition=_check_critical_error,
    reaction=_react_critical_error,
    priority=20 # High priority
)
