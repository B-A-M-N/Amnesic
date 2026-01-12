import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.policies import _check_mission_complete, _react_mission_complete, _check_critical_error, _react_critical_error
from amnesic.presets.code_agent import FrameworkState, Artifact

class TestPoliciesUnit(unittest.TestCase):
    def setUp(self):
        self.state = FrameworkState(
            task_intent="Test Mission",
            current_hypothesis="Testing",
            hard_constraints=[],
            confidence_score=1.0
        )

    def test_mission_complete_policy_trigger(self):
        """Verify mission complete triggers only with both TOTAL and VERIFICATION/Feedback."""
        # 1. Only TOTAL - Should NOT trigger usually (unless Feedback matches)
        self.state.artifacts = [Artifact(identifier="TOTAL", type="result", summary="42", status="committed")]
        self.assertFalse(_check_mission_complete(self.state))
        
        # 2. Add VERIFICATION - Should trigger
        self.state.artifacts.append(Artifact(identifier="VERIFICATION", type="result", summary="Passed", status="committed"))
        self.assertTrue(_check_mission_complete(self.state))
        
        # 3. Reaction should return halt_and_ask
        move = _react_mission_complete(self.state)
        self.assertEqual(move.tool_call, "halt_and_ask")
        self.assertIn("TOTAL: 42", move.target)

    def test_mission_complete_feedback_override(self):
        """Verify mission complete triggers with TOTAL and 'COMPLETE' in feedback."""
        self.state.artifacts = [Artifact(identifier="TOTAL", type="result", summary="42", status="committed")]
        self.state.last_action_feedback = "Mission is now COMPLETE."
        self.assertTrue(_check_mission_complete(self.state))

    def test_critical_error_policy(self):
        """Verify critical error triggers halt."""
        self.state.last_action_feedback = "CRITICAL ERROR: File not found"
        self.assertTrue(_check_critical_error(self.state))
        
        move = _react_critical_error(self.state)
        self.assertEqual(move.tool_call, "halt_and_ask")
        self.assertIn("CRITICAL ERROR", move.target)

    def test_violation_triggers_immediate_halt(self):
        """Verify CONTRACT VIOLATION triggers immediate halt without verification artifact."""
        self.state.artifacts = [Artifact(identifier="CONTRACT_VIOLATION", type="error_log", summary="Mismatch", status="needs_review")]
        self.assertTrue(_check_mission_complete(self.state))

if __name__ == "__main__":
    unittest.main()
