import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact, ManagerMove

class TestFeasibilityUnit(unittest.TestCase):
    def setUp(self):
        self.session = AmnesicSession(mission="Feasibility Test")
        self.session.driver = MagicMock()

    def test_self_correction_artifact_overwrite(self):
        """Verify that _tool_worker_task overwrites existing artifacts (Self-Correction)."""
        # 1. Setup initial artifact
        self.session.state['framework_state'].artifacts = [
            Artifact(identifier="SECRET", type="text_content", summary="old_val", status="verified_invariant")
        ]
        
        # 2. Mock worker to return new value
        with patch('amnesic.decision.worker.Worker.execute_task') as mock_worker:
            mock_worker.return_value = MagicMock(content="new_val")
            
            # 3. Execute tool
            self.session._tool_worker_task("SECRET")
            
        # 4. Verify overwrite
        arts = self.session.state['framework_state'].artifacts
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0].summary, "new_val")
        self.assertIn("Artifact SECRET saved.", self.session.state['framework_state'].last_action_feedback)

    def test_marathon_turn_tracking(self):
        """Verify that session turn count increments correctly over many steps."""
        # We manually step the nodes or pager
        for i in range(50):
            self.session.pager.tick()
            
        self.assertEqual(self.session.pager.current_turn, 50)

    def test_extreme_efficiency_low_capacity(self):
        """Verify session initializes and operates with extremely low L1 capacity."""
        tiny_session = AmnesicSession(mission="Tiny", l1_capacity=100)
        self.assertEqual(tiny_session.pager.capacity, 100)
        
        # Verify it can still pin the mission (which is tiny)
        self.assertIn("SYS:MISSION", tiny_session.pager.l1_active)
        
        # Verify it rejects a moderately large file
        large_content = "Word " * 200 # ~200 tokens
        success = tiny_session.pager.request_access("FILE:test.py", large_content)
        self.assertFalse(success)

if __name__ == "__main__":
    unittest.main()
