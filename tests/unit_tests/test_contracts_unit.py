import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class TestContractsUnit(unittest.TestCase):
    def setUp(self):
        self.session = AmnesicSession(mission="Contract Test")
        self.session.driver = MagicMock()

    def test_verify_step_semantic_pass(self):
        """Verify _tool_verify_step passes when text is in L1."""
        self.session.pager.request_access("FILE:test.txt", "The contract is signed.")
        
        self.session._tool_verify_step("signed")
        
        arts = self.session.state['framework_state'].artifacts
        verif = next(a for a in arts if a.identifier == "VERIFICATION")
        self.assertIn("PASSED", verif.summary)
        self.assertIn("'signed' verified", verif.summary)

    def test_verify_step_semantic_fail(self):
        """Verify _tool_verify_step reports missing text."""
        self.session.pager.request_access("FILE:test.txt", "Empty")
        
        self.session._tool_verify_step("missing_keyword")
        
        arts = self.session.state['framework_state'].artifacts
        verif = next(a for a in arts if a.identifier == "VERIFICATION")
        self.assertIn("'missing_keyword' is NOT present", verif.summary)

    def test_verify_step_math_logic(self):
        """Verify _tool_verify_step performs math based on artifact content."""
        self.session.state['framework_state'].artifacts = [
            Artifact(identifier="A", type="text_content", summary="100", status="staged"),
            Artifact(identifier="B", type="text_content", summary="200", status="staged")
        ]
        
        self.session._tool_verify_step("MULTIPLY A and B")
        
        arts = self.session.state['framework_state'].artifacts
        total = next(a for a in arts if a.identifier == "TOTAL")
        self.assertIn("20000", total.summary)

if __name__ == "__main__":
    unittest.main()
