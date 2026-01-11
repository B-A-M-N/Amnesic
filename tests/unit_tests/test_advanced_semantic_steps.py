import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession, AgentState
from amnesic.presets.code_agent import FrameworkState, Artifact

class TestAdvancedSemanticSteps(unittest.TestCase):
    def setUp(self):
        self.session = AmnesicSession(mission="Advanced Test", l1_capacity=1500)
        self.session.driver = MagicMock()
        self.session.manager_node.driver = self.session.driver

    def test_protocol_logic_add(self):
        """Verify _tool_verify_step handles ADD protocol correctly."""
        # Setup state
        self.session.state['framework_state'].artifacts = [
            Artifact(identifier="PROTOCOL", type="text_content", summary="Must ADD them", status="verified_invariant"),
            Artifact(identifier="VAL_A", type="text_content", summary="10", status="verified_invariant"),
            Artifact(identifier="VAL_B", type="text_content", summary="20", status="verified_invariant")
        ]
        
        # Execute
        self.session._tool_verify_step("execute_logic")
        
        # Verify
        arts = self.session.state['framework_state'].artifacts
        total = next(a for a in arts if a.identifier == "TOTAL")
        self.assertIn("30", total.summary)
        self.assertIn("ADD", total.summary)

    def test_protocol_logic_multiply(self):
        """Verify _tool_verify_step handles MULTIPLY protocol correctly."""
        # Setup state
        self.session.state['framework_state'].artifacts = [
            Artifact(identifier="PROTOCOL", type="text_content", summary="Must MULTIPLY them", status="verified_invariant"),
            Artifact(identifier="VAL_A", type="text_content", summary="5", status="verified_invariant"),
            Artifact(identifier="VAL_B", type="text_content", summary="4", status="verified_invariant")
        ]
        
        # Execute
        self.session._tool_verify_step("execute_logic")
        
        # Verify
        arts = self.session.state['framework_state'].artifacts
        total = next(a for a in arts if a.identifier == "TOTAL")
        self.assertIn("20", total.summary)
        self.assertIn("MULTIPLY", total.summary)

    def test_intent_recovery_worker(self):
        """Verify Worker system prompt includes Intent Recovery instructions."""
        # This tests the configuration, not the LLM output directly
        from amnesic.decision.worker import Worker
        worker = Worker(self.session.driver)
        
        # We can't easily inspect the internal prompt construction of execute_task without mocking the driver call
        # and checking the args passed to it.
        with patch.object(self.session.driver, 'generate_structured') as mock_gen:
            worker.execute_task("Find VAL_A", "not_val_a = 10", ["Output raw"])
            
            # Check if system prompt contains key phrases
            call_args = mock_gen.call_args
            system_prompt = call_args.kwargs['system_prompt']
            self.assertIn("intentionally misleading", system_prompt)
            self.assertIn("Recover the INTENT", system_prompt)

if __name__ == "__main__":
    unittest.main()
