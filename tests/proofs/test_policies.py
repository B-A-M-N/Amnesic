from amnesic.core.policies import KernelPolicy
from amnesic.presets.code_agent import FrameworkState, ManagerMove

def _check_total_artifact(state: FrameworkState) -> bool:
    """Trigger: When 'TOTAL' artifact exists."""
    return any(a.identifier == "TOTAL" for a in state.artifacts)

def _react_report_total(state: FrameworkState) -> ManagerMove:
    """Action: Halt and report the total."""
    total_val = next(a.summary for a in state.artifacts if a.identifier == "TOTAL")
    return ManagerMove(
        thought_process="Policy Trigger: TOTAL artifact found. Mission Complete.",
        tool_call="halt_and_ask",
        target=total_val
    )

# The standard policy for our math-based proofs
PROOF_COMPLETION_POLICY = KernelPolicy(
    name="ProofCompletion",
    condition=_check_total_artifact,
    reaction=_react_report_total,
    priority=10
)

def _check_deadlock(state: FrameworkState) -> bool:
    """Trigger: If turn count exceeds 20 (Safety)."""
    return len(state.decision_history) > 20

def _react_kill_switch(state: FrameworkState) -> ManagerMove:
    return ManagerMove(
        thought_process="Policy Trigger: Deadlock detected (Max Turns). Halting.",
        tool_call="halt_and_ask",
        target="TIMEOUT"
    )

SAFETY_NET_POLICY = KernelPolicy(
    name="SafetyNet",
    condition=_check_deadlock,
    reaction=_react_kill_switch,
    priority=100 # High priority override
)
