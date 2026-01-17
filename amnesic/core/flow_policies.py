import re
from amnesic.core.policies import KernelPolicy
from amnesic.presets.code_agent import FrameworkState, ManagerMove

def create_warm_start_linker(keywords: list, priority: int = 15):
    """
    Creates a policy that automatically stages artifacts from the Backpack 
    into L1 RAM if the Mission requires them.
    
    Keywords: List of strings to match in Mission text and Artifact IDs.
    """
    
    def _condition(state: FrameworkState, active_pages: list):
        mission_text = state.task_intent.upper()
        # 1. Does the mission mention our target flow?
        mission_match = any(k.upper() in mission_text for k in keywords)
        if not mission_match: return False
        
        # 2. Are there relevant artifacts in the Backpack?
        matching_artifacts = [
            a.identifier for a in state.artifacts 
            if any(k.upper() in a.identifier.upper() for k in keywords)
        ]
        if not matching_artifacts: return False
        
        # 3. ANTI-LOOP: Are they ALREADY in L1 RAM?
        # Check the actual pager state provided by the Manager
        for art_id in matching_artifacts:
            if f"ARTIFACT:{art_id}" in active_pages:
                return False
            
        return True

    def _reaction(state: FrameworkState):
        matching_artifacts = [
            a.identifier for a in state.artifacts 
            if any(k.upper() in a.identifier.upper() for k in keywords)
        ]
        target_str = " ".join(matching_artifacts)
        
        return ManagerMove(
            thought_process=f"Flow Linker Detected: Mission requires {keywords} data. Pre-staging artifacts [{target_str}] from Backpack.",
            tool_call="stage_multiple_artifacts",
            target=target_str
        )

    return KernelPolicy(
        name=f"WarmStartLinker_{'_'.join(keywords)}",
        condition=_condition,
        reaction=_reaction,
        priority=priority
    )

# Pre-defined Linkers for common flows
NET_SEC_LINKER = create_warm_start_linker(["NET", "SEC"])
CONTRACT_LINKER = create_warm_start_linker(["CONTRACT", "SPEC"])
PAYROLL_LINKER = create_warm_start_linker(["EMPLOYEE", "PAYROLL", "SALARY"])
