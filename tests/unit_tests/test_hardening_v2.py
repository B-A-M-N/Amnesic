import unittest
import os
import sys
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic import AmnesicSession, Artifact

class TestHardeningV2(unittest.TestCase):
    def setUp(self):
        self.session = AmnesicSession(mission="Test")
        self.session.driver = MagicMock()

    def test_artifact_symbolic_integrity(self):
        """Guarantee: Artifact identifiers MUST be symbolic (no prose)."""
        # 1. Attempt to save an artifact with prose via the tool
        # We need to mock the worker to return a valid string content
        with unittest.mock.patch('amnesic.decision.worker.Worker.execute_task') as mock_worker:
            mock_worker.return_value = MagicMock(content="42")
            self.session._tool_worker_task("The result is 42")
        
        # 2. Verify it was normalized
        art = self.session.state['framework_state'].artifacts[0]
        self.assertNotIn(" ", art.identifier)
        self.assertEqual(art.identifier, "The_result_is_42")

    def test_state_rollback_reliability(self):
        """Guarantee: Snapshot/Restore must perfectly revert state."""
        # 1. Save initial state
        self.session.state['framework_state'].artifacts.append(
            Artifact(identifier="TRUTH", type="result", summary="1", status="committed")
        )
        self.session.snapshot_state("T1")
        
        # 2. Corrupt state
        self.session.state['framework_state'].artifacts = [
            Artifact(identifier="POISON", type="result", summary="bad", status="needs_review")
        ]
        
        # 3. Restore
        self.session.restore_state("T1")
        
        # 4. Verify
        arts = self.session.state['framework_state'].artifacts
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0].identifier, "TRUTH")

    def test_auditor_hygiene_rejection(self):
        """Guarantee: Auditor must reject moves that attempt to store dirty state."""
        from amnesic.decision.manager import ManagerMove
        
        # Move with prose in the target
        bad_move = ManagerMove(
            thought_process="Saving data",
            tool_call="save_artifact",
            target="This is not a symbolic key"
        )
        
        self.session.state['manager_decision'] = bad_move
        result = self.session.graph._node_auditor(self.session.state)
        
        self.assertEqual(result['last_audit']['auditor_verdict'], "REJECT")
        self.assertIn("SEMANTIC POLLUTION", result['last_audit']['rationale'])

    def test_context_ejection_guarantee(self):
        """Guarantee: unstage_context physically removes data from L1."""
        # 1. Stage a file
        self.session.pager.request_access("FILE:test.py", "content", priority=8)
        self.assertIn("FILE:test.py", self.session.pager.active_pages)
        
        # 2. Unstage
        self.session._tool_unstage("test.py")
        
        # 3. Verify L1 is physically empty
        self.assertNotIn("FILE:test.py", self.session.pager.active_pages)

if __name__ == "__main__":
    unittest.main()
