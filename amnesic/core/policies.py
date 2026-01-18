import re
from typing import Callable, Optional, List
from dataclasses import dataclass
from amnesic.presets.code_agent import FrameworkState, ManagerMove

@dataclass
class KernelPolicy:
    """
    A deterministic rule that overrides the LLM Manager.
    Used for safety rails, mission completion triggers, or forced context wipes.
    """
    name: str
    condition: Callable[[FrameworkState, List[str]], bool]
    reaction: Callable[[FrameworkState], ManagerMove]
    priority: int = 10  # Higher runs first

# --- Default Policies ---

def _check_mission_complete(state: FrameworkState) -> bool:
    """Detects if the mission goal has been achieved via artifacts."""
    mission = state.task_intent.lower()
    
    # 1. MATH/TOTAL COMPLETION: If the mission asks for a sum/total and we have it.
    has_total = any(a and a.identifier == "TOTAL" for a in state.artifacts)
    is_math_mission = any(kw in mission for kw in ["sum", "total", "calculate", "math", "add", "result"])
    if has_total and is_math_mission:
        return True

    # 2. COUNT-BASED COMPLETION
    count_match = re.search(r"(\d+)\s*(-word|\s*parts|\s*artifacts|\s*files|\s*values|\s*items)", mission)
    if count_match:
        required_count = int(count_match.group(1))
        # Find parts (ignore metadata)
        actual_parts = [a for a in state.artifacts if a and (a.identifier.startswith("PART_") or a.identifier.startswith("VAL_") or a.identifier.startswith("FUNC_"))]
        if len(actual_parts) >= required_count:
            return True
        
    # Standard completion patterns...
    if not state.artifacts:
        return False
def _react_mission_complete(state: FrameworkState) -> ManagerMove:
    """Forces a halt when mission is complete."""
    # RESPECT FORBIDDEN TOOLS: If halt is forbidden (e.g. Pipeline Reporter must write file first),
    # do not force a halt. Let the agent continue.
    # We need to access the forbidden_tools from the wrapper state, but here we only have FrameworkState.
    # However, the Manager checks this before calling policies? No.
    # Policies run *before* Manager.
    # We can't easily access forbidden_tools here without changing the signature.
    # WAIT: FrameworkState doesn't have forbidden_tools. AgentState does.
    # But this function takes FrameworkState.
    
    # HACK: We can infer it's the Reporter step if the artifacts contain 'TOTAL' 
    # but we haven't written the file yet? No.
    
    # BETTER FIX: We will modify the DEFAULT_COMPLETION_POLICY instantiation below 
    # to use a lambda that checks the FULL AgentState if possible, or just accept 
    # that we need to change the function signature in a future refactor.
    
    # For now, let's look at the Artifacts. If we have TOTAL, but the mission explicitly says "write_file", 
    # maybe we should wait?
    mission = state.task_intent.lower()
    has_total = any(a.identifier == "TOTAL" for a in state.artifacts if a)
    
    # If mission says "write" and we haven't written yet (heuristic: check history for write_file success)
    if "write" in mission and has_total:
        # Check if we recently wrote a file
        wrote_file = any(h.get('tool_call') == 'write_file' and h.get('execution_result') == 'SUCCESS' for h in state.decision_history)
        if not wrote_file:
            # We have the total, but haven't written it yet. HOLD FIRE.
            return None

    # Find the most relevant completion artifact
    art = next((a for a in state.artifacts if a and a.identifier == "TOTAL"), None)
    
    # IMPROVEMENT: If this is a concatenation mission (Marathon), 
    # ensure the TOTAL artifact actually contains all the parts.
    mission_text = state.task_intent.lower()
    if "concatenat" in mission_text or "10-word" in mission_text or "all parts" in mission_text:
        all_parts = sorted([a for a in state.artifacts if a and a.identifier.startswith("PART_")], key=lambda x: x.identifier)
        if all_parts:
            combined = " ".join([p.summary.strip("'\"") for p in all_parts])
            return ManagerMove(
                thought_process=f"Mission complete. All {len(all_parts)} parts combined.",
                tool_call="halt_and_ask",
                target=f"TOTAL: {combined}"
            )

    if not art:
        art = next((a for a in state.artifacts if a and "VIOLATION" in a.identifier.upper()), None)
    if not art:
        art = next((a for a in state.artifacts if a and "COMPLETE" in a.identifier.upper()), None)
    if not art:
        art = next((a for a in state.artifacts if a and "VERIFICATION" in a.identifier.upper()), None)
    
    return ManagerMove(
        thought_process=f"The {art.identifier} artifact is present. The mission is complete.",
        tool_call="halt_and_ask",
        target=f"{art.identifier}: {art.summary}"
    )

# The default "Hardcoded" behavior, now essentially a plugin
DEFAULT_COMPLETION_POLICY = KernelPolicy(
    name="CompletionPolicy",
    condition=lambda state, active_pages: _check_mission_complete(state),
    reaction=lambda state: _react_mission_complete(state)
)

def _check_critical_error(state: FrameworkState, active_pages: List[str]) -> bool:
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

def _check_l1_violation(state: FrameworkState, active_pages: List[str]) -> bool:
    """Trigger: If the last move failed because L1 was full."""
    return state.last_action_feedback and "L1 RAM VIOLATION" in state.last_action_feedback

def _react_l1_violation(state: FrameworkState) -> ManagerMove:
    """Forces an unstage of the blocking file."""
    # Feedback format: "... (FILE:step_0.txt is open)..."
    blocker = "unknown"
    match = re.search(r"FILE:([^\s]+) is open", state.last_action_feedback)
    if match:
        blocker = match.group(1)
        
    return ManagerMove(
        thought_process=f"L1 Violation Policy: Memory is full. Forcing unstage of {blocker} to clear path.",
        tool_call="unstage_context",
        target=blocker
    )

L1_VIOLATION_POLICY = KernelPolicy(
    name="L1ViolationHandler",
    condition=_check_l1_violation,
    reaction=_react_l1_violation,
    priority=25 # Higher than critical error, lower than progress lock? No, high priority to fix immediate block.
)

def _check_progress_lock(state: FrameworkState, active_pages: List[str]) -> bool:
    """Trigger: If mission requires N parts, but we have < N."""
    mission_text = state.task_intent.lower()
    # Match "all 10 words", "all 16 values", "3 steps", etc.
    count_match = re.search(r"all (\d+)|(\d+) (words|values|files|parts|artifacts|steps)", mission_text)
    if not count_match:
        return False
        
    required = int(count_match.group(1) or count_match.group(2))
    # Count non-meta artifacts
    current_count = len([a for a in state.artifacts if a and a.identifier not in ["TOTAL", "VERIFICATION", "FILE_LIST"]])
    
    last_feedback = state.last_action_feedback or ""
    is_short = current_count < required
    
    # Trigger if agent tries to halt or calculate too early
    premature_intent = "halt_and_ask" in str(state.decision_history[-1].get('tool_call', '')) if state.decision_history else False
    if "calculate" in last_feedback.lower() or "halt" in last_feedback.lower():
        premature_intent = True

    # ANTI-INTERFERENCE: If L1 is occupied in strict mode, do NOT lock progress.
    # Let the Manager (or other policies) handle the unstage.
    # We assume strict mode if elastic_mode is False.
    if not state.elastic_mode and len(active_pages) > 0:
        return False

    return is_short and premature_intent

def _react_progress_lock(state: FrameworkState) -> ManagerMove:
    mission_text = state.task_intent.lower()
    count_match = re.search(r"all (\d+)|(\d+) (words|values|files|parts|artifacts|steps)", mission_text)
    required = int(count_match.group(1) or count_match.group(2))
    current_count = len([a for a in state.artifacts if a and a.identifier not in ["TOTAL", "VERIFICATION", "FILE_LIST"]])
    
    # Logic to find the next logical file
    if "step_" in mission_text or any(a and "step_" in a.identifier for a in state.artifacts):
        next_idx = current_count
        target_file = f"step_{next_idx}.txt"
    else:
        next_idx = f"{current_count:02d}"
        target_file = f"log_{next_idx}.txt"
    
    # ANTI-LOCK: If strict mode and L1 is full, force unstage first.
    # We infer strict mode if 'elastic_mode' is False in state (default assumption if missing)
    elastic_mode = getattr(state, 'elastic_mode', False)
    # Check if L1 has user files (heuristic via last feedback or history is hard, 
    # but we can infer from the rejection loop)
    last_rejection = "L1 RAM VIOLATION" in (state.last_action_feedback or "")
    
    if not elastic_mode and last_rejection:
        # Extract the file blocking L1 from the feedback string if possible
        # "Memory is full (FILE:step_0.txt is open)"
        blocker_match = re.search(r"FILE:([^\s]+) is open", state.last_action_feedback)
        if blocker_match:
            blocker = blocker_match.group(1)
            return ManagerMove(
                thought_process=f"PROGRESS LOCK: L1 is full ({blocker}). Unstaging before proceeding to {target_file}.",
                tool_call="unstage_context",
                target=blocker
            )

    return ManagerMove(
        thought_process=f"PROGRESS LOCK: I only have {current_count}/{required} artifacts. I MUST continue gathering data. Next step: stage_context({target_file}).",
        tool_call="stage_context",
        target=target_file
    )

def _check_auto_halt(state: FrameworkState, active_pages: List[str]) -> bool:
    """Trigger: Simple missions that just need to extract and stop."""
    mission_text = state.task_intent.lower()
    
    # FORBIDDEN in Restricted mode (e.g. Phase 3 composition)
    # Composition requires multiple pieces, not a simple extract-and-halt.
    if "SNAPSHOT MODE" in str(state.decision_history) or "RESTRICTED" in str(state.decision_history):
        return False

    # If mission has multiple steps or "then", it's NOT simple
    is_complex = any(kw in mission_text for kw in ["1.", "2.", "then", "finally", "after", "compare", "synthesize", "combine", "follow", "trail"])
    is_simple = "extract" in mission_text and not is_complex
    
    if not is_simple: return False
    
    # MISSION SPECIFICITY: Look for a target name in the mission (e.g. 'FUNC_{item}')
    target_matches = re.findall(r"artifact ['\"]?([^'\"\s]+)['\"]?", mission_text)
    
    if target_matches:
        target_name = target_matches[-1] # Take the last one mentioned (usually the goal)
        return any(a and a.identifier.lower() == target_name.lower() for a in state.artifacts)

    # Fallback: If no specific name mentioned, any new non-meta artifact counts
    return any(a and a.identifier not in ["TOTAL", "VERIFICATION", "FILE_LIST"] for a in state.artifacts)

def _react_auto_halt(state: FrameworkState) -> ManagerMove:
    art = next(a for a in state.artifacts if a and a.identifier not in ["TOTAL", "VERIFICATION"])
    return ManagerMove(
        thought_process=f"AutoHalt: Mission required extraction, and '{art.identifier}' is saved. Mission complete.",
        tool_call="halt_and_ask",
        target=f"{art.identifier} saved."
    )

def _check_stagnation_breaker(state: FrameworkState, active_pages: List[str]) -> bool:
    """Trigger: If last 4 turns were rejections of the same move."""
    history = state.decision_history
    if len(history) < 4: return False
    
    last_window = history[-4:]
    all_rejected = all(h.get('auditor_verdict') == "REJECT" for h in last_window)
    same_tool = len(set(h.get('tool_call') for h in last_window)) == 1
    
    return all_rejected and same_tool

def _react_stagnation_breaker(state: FrameworkState) -> ManagerMove:
    # Force a jump to the next expected file
    current_count = len([a for a in state.artifacts if a and a.identifier not in ["TOTAL", "VERIFICATION", "FILE_LIST"]])
    mission_text = state.task_intent.lower()
    
    if "step_" in mission_text or any(a and "step_" in a.identifier for a in state.artifacts):
        next_idx = current_count
        target_file = f"step_{next_idx}.txt"
    else:
        # Fallback for log missions
        next_idx = f"{current_count:02d}"
        target_file = f"log_{next_idx}.txt"
    
    return ManagerMove(
        thought_process=f"STAGNATION BREAKER: Multiple rejections detected. Forcing progress to {target_file}. UNSTAGING current context.",
        tool_call="unstage_context",
        target="ALL"
    )

STAGNATION_BREAKER_POLICY = KernelPolicy(
    name="StagnationBreaker",
    condition=_check_stagnation_breaker,
    reaction=_react_stagnation_breaker,
    priority=40 # Very high priority
)

AUTO_HALT_POLICY = KernelPolicy(
    name="AutoHalt",
    condition=_check_auto_halt,
    reaction=_react_auto_halt,
    priority=5 # Lower than progress lock
)

PROGRESS_LOCK_POLICY = KernelPolicy(
    name="ProgressLock",
    condition=_check_progress_lock,
    reaction=_react_progress_lock,
    priority=30 
)
