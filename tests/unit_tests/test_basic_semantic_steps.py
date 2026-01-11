import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession, AgentState
from amnesic.presets.code_agent import FrameworkState, Artifact, ManagerMove

class TestBasicSemanticSteps(unittest.TestCase):
    def setUp(self):
        # Initialize session with minimal capacity
        self.session = AmnesicSession(mission="Test Mission", l1_capacity=1500)
        
        # Mock Driver
        self.mock_driver = MagicMock()
        self.session.driver = self.mock_driver
        self.session.manager_node.driver = self.mock_driver
        
        # Mock Environment
        self.session.env = MagicMock()
        self.session.env.refresh_substrate.return_value = []
        
    def test_step_1_auditor_enforcement(self):
        """Test Step 1: Auditor enforcing single-file limit."""
        # 1. State with no files
        state: AgentState = {
            "framework_state": self.session.state["framework_state"],
            "active_file_map": [{"path": "test.txt"}],
            "manager_decision": ManagerMove(thought_process="I need to stage the file for analysis.", tool_call="stage_context", target="test.txt"),
            "last_audit": None,
            "last_node": "manager"
        }
        
        # Auditor should PASS
        result = self.session._node_auditor(state)
        self.assertEqual(result["last_audit"]["auditor_verdict"], "PASS")
        
        # 2. Add a file to L1
        self.session.pager.pin_page("FILE:old.txt", "content")
        
        # Auditor should REJECT a second stage
        result = self.session._node_auditor(state)
        self.assertEqual(result["last_audit"]["auditor_verdict"], "REJECT")
        self.assertIn("L1 Violation", result["last_audit"]["rationale"])

    def test_step_2_executor_auto_evict(self):
        """Test Step 2: Executor clearing L1 after save_artifact."""
        # 1. Load a file
        self.session.pager.request_access("FILE:target.txt", "some data")
        self.assertIn("FILE:target.txt", self.session.pager.active_pages)
        
        # 2. Mock a PASSing save_artifact move
        state: AgentState = {
            "framework_state": self.session.state["framework_state"],
            "manager_decision": ManagerMove(thought_process="I am saving the value to an artifact now.", tool_call="save_artifact", target="val_x"),
            "last_audit": {"auditor_verdict": "PASS"},
            "last_node": "auditor"
        }
        
        # 3. Execute - Mock Worker
        with patch('amnesic.decision.worker.Worker.execute_task') as mock_worker:
            mock_worker.return_value = MagicMock(content="42")
            self.session._node_executor(state)
            
        # 4. Verify L1 is cleared
        self.assertNotIn("FILE:target.txt", self.session.pager.active_pages)
        self.assertIn("FILE:target.txt", self.session.pager.swap_disk)

    def test_step_3_verify_logic(self):
        """Test Step 3: verify_step tool sums X + Y and creates TOTAL artifact."""
        # 1. Add X and Y artifacts
        self.session.state["framework_state"].artifacts = [
            Artifact(identifier="val_x", type="text_content", summary="val_x = 10", status="staged"),
            Artifact(identifier="val_y", type="text_content", summary="val_y = 20", status="staged")
        ]
        
        # 2. Execute verify_step
        # Note: _tool_verify_step now requires a keyword like 'SUM' or 'ADD' to trigger math
        self.session._tool_verify_step("ADD val_x and val_y")
            
        # 3. Verify TOTAL artifact
        artifacts = self.session.state["framework_state"].artifacts
        final_art = next((a for a in artifacts if a.identifier == "TOTAL"), None)
        self.assertIsNotNone(final_art)
        self.assertIn("30", final_art.summary)

    def test_step_4_manager_completion_override(self):
        """Test Step 4: Manager deterministically overrides to halt_and_ask when TOTAL is found."""
        # 1. Setup state with TOTAL
        self.session.state["framework_state"].artifacts = [
            Artifact(identifier="TOTAL", type="result", summary="58", status="committed")
        ]
        
        # 2. Run Manager - NO Driver Mock needed because it should override!
        state: AgentState = {
            "framework_state": self.session.state["framework_state"],
            "active_file_map": [],
            "manager_decision": None,
            "last_audit": None,
            "last_node": None
        }
        
        result = self.session._node_manager(state)
        
        # 3. Verify override
        move = result["manager_decision"]
        self.assertEqual(move.tool_call, "halt_and_ask")
        self.assertEqual(move.target, "58")
        self.assertIn("mission is complete", move.thought_process)

if __name__ == "__main__":
    unittest.main()