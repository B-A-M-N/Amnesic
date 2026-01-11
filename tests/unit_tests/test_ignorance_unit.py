import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession, AgentState
from amnesic.decision.manager import ManagerMove

class TestIgnoranceUnit(unittest.TestCase):
    def setUp(self):
        self.session = AmnesicSession(mission="Ignorance Test")
        self.session.driver = MagicMock()

    def test_auditor_rejects_missing_file(self):
        """Verify that Auditor REJECTS a stage_context move for a non-existent file."""
        move = ManagerMove(
            thought_process="I need to read this mystery file.",
            tool_call="stage_context",
            target="missing_file.py"
        )
        
        # Setup state for auditor node
        state: AgentState = {
            "framework_state": self.session.state['framework_state'],
            "active_file_map": [], # Empty map = no files on disk
            "manager_decision": move,
            "last_audit": None,
            "tool_output": None,
            "last_node": "manager"
        }
        
        # Run node auditor
        result = self.session._node_auditor(state)
        
        # Verify rejection
        self.assertEqual(result['last_audit']['auditor_verdict'], "REJECT")
        self.assertIn("does not exist", result['last_audit']['rationale'])

if __name__ == "__main__":
    unittest.main()
