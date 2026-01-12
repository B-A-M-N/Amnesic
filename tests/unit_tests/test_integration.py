import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import ManagerMove, Artifact

class TestFrameworkIntegration(unittest.TestCase):
    def setUp(self):
        self.config = {"configurable": {"thread_id": "integration_test"}}

    def test_integration_island_hop(self):
        """Integration: Basic Semantic Retrieval (Island Hop)"""
        with open("island_a.txt", "w") as f: f.write("val_x = 10")
        with open("island_b.txt", "w") as f: f.write("val_y = 20")
        
        session = AmnesicSession(mission="Sum val_x and val_y", l1_capacity=1500)
        mock_driver = MagicMock()
        session.driver = mock_driver
        session.manager_node.driver = mock_driver
        # Ensure Auditor also uses the mock
        session.auditor_node.driver = mock_driver
        
        # Mock Auditor to always PASS
        from amnesic.presets.code_agent import AuditorVerdict
        mock_driver.generate_structured.return_value = AuditorVerdict(
            outcome="PASS", risk_level="low", rationale="Mock pass"
        )

        # STRICT AMNESIC SEQUENCE: Stage -> Save -> Unstage -> Stage -> Save -> Calculate -> Halt
        mock_driver.generate_structured_with_stream.side_effect = [
            ManagerMove(thought_process="Staging island_a.txt now.", tool_call="stage_context", target="island_a.txt"),
            ManagerMove(thought_process="Saving val_x to artifacts.", tool_call="save_artifact", target="val_x"),
            ManagerMove(thought_process="Unstaging island_a.txt now.", tool_call="unstage_context", target="island_a.txt"),
            ManagerMove(thought_process="Staging island_b.txt now.", tool_call="stage_context", target="island_b.txt"),
            ManagerMove(thought_process="Saving val_y to artifacts.", tool_call="save_artifact", target="val_y"),
            ManagerMove(thought_process="Unstaging island_b.txt now.", tool_call="unstage_context", target="island_b.txt"),
            ManagerMove(thought_process="Calculating the final sum.", tool_call="calculate", target="val_x + val_y"),
            ManagerMove(thought_process="Mission complete. Reporting final sum.", tool_call="halt_and_ask", target="30")
        ]

        with patch('amnesic.decision.worker.Worker.execute_task') as mock_worker:
            mock_worker.side_effect = [MagicMock(content="10"), MagicMock(content="20")]
            session.run(config=self.config)

        artifacts = session.state['framework_state'].artifacts
        self.assertTrue(any(a.identifier == "TOTAL" and "30" in a.summary for a in artifacts))
        
        for f in ["island_a.txt", "island_b.txt"]: 
            if os.path.exists(f): os.remove(f)

    def test_integration_code_fix(self):
        """Integration: Basic Code Modification (Junior Dev Fix)"""
        with open("app.py", "w") as f: f.write("rate = 0.5")
        
        session = AmnesicSession(mission="Change 0.5 to 0.05", l1_capacity=1500)
        mock_driver = MagicMock()
        session.driver = mock_driver
        session.manager_node.driver = mock_driver
        session.auditor_node.driver = mock_driver

        # Mock Auditor to always PASS
        from amnesic.presets.code_agent import AuditorVerdict
        mock_driver.generate_structured.return_value = AuditorVerdict(
            outcome="PASS", risk_level="low", rationale="Mock pass"
        )

        with patch('amnesic.decision.worker.Worker.perform_edit') as mock_worker:
            mock_worker.return_value = MagicMock(original_snippet="0.5", new_snippet="0.05")
            
            mock_driver.generate_structured_with_stream.side_effect = [
                ManagerMove(thought_process="Staging app.py to identify bug", tool_call="stage_context", target="app.py"),
                ManagerMove(thought_process="Editing app.py to fix tax rate", tool_call="edit_file", target="app.py: set to 0.05"),
                ManagerMove(thought_process="Halt and report success of patch", tool_call="halt_and_ask", target="Patched")
            ]

            session.run(config=self.config)

        with open("app.py", "r") as f: content = f.read()
        self.assertEqual(content, "rate = 0.05")
        if os.path.exists("app.py"): os.remove("app.py")

if __name__ == "__main__":
    unittest.main()