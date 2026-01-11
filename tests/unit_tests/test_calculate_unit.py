import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class TestCalculateTool(unittest.TestCase):
    def setUp(self):
        # Initialize a session with a dummy model to avoid API calls
        self.session = AmnesicSession(model="dummy-model", l1_capacity=1000)
        # Mock the driver to prevent actual LLM calls during initialization or execution
        self.session.driver = MagicMock()
        self.session.sidecar = None # Disable sidecar for unit testing
        
        # Clear artifacts for each test
        self.session.state['framework_state'].artifacts = []

    def test_calculate_addition_symbol(self):
        """Test calculation using '+' symbol."""
        self.session._tool_calculate("10 + 20")
        self._assert_total(30, "ADD")

    def test_calculate_subtraction_symbol(self):
        """Test calculation using '-' symbol."""
        self.session._tool_calculate("50 - 20")
        self._assert_total(30, "SUBTRACT")

    def test_calculate_multiplication_symbol(self):
        """Test calculation using '*' symbol."""
        self.session._tool_calculate("5 * 6")
        self._assert_total(30, "MULTIPLY")

    def test_calculate_division_symbol(self):
        """Test calculation using '/' symbol."""
        self.session._tool_calculate("60 / 2")
        self._assert_total(30.0, "DIVIDE")

    def test_calculate_legacy_words(self):
        """Test calculation using legacy keywords (regression)."""
        self.session._tool_calculate("ADD 10 and 20")
        self._assert_total(30, "ADD")

    def test_calculate_with_artifacts(self):
        """Test calculation resolving values from existing artifacts."""
        # Seed artifacts
        self.session.state['framework_state'].artifacts.append(
            Artifact(identifier="val_x", type="text_content", summary="100", status="verified_invariant")
        )
        self.session.state['framework_state'].artifacts.append(
            Artifact(identifier="val_y", type="text_content", summary="50", status="verified_invariant")
        )

        # Test implicit artifact resolution via summary text injection in _tool_calculate
        # The tool concatenates all artifact summaries, so "100" and "50" are available.
        # The target string just needs to imply the operation on them.
        self.session._tool_calculate("val_x + val_y")
        
        # Expect 100 + 50 = 150. 
        # Note: The current implementation greps all numbers from artifacts + target.
        # It doesn't strictly variable bind, but for this test suite we verify the logic holds.
        self._assert_total(150, "ADD")

    def _assert_total(self, expected_value, expected_op):
        """Helper to verify the TOTAL artifact."""
        artifacts = self.session.state['framework_state'].artifacts
        total_artifact = next((a for a in artifacts if a.identifier == "TOTAL"), None)
        
        self.assertIsNotNone(total_artifact, "TOTAL artifact was not created")
        
        # Check value matches (handling int/float differences)
        # Summary format: "Final Calculation ({OP}): {RESULT}"
        self.assertIn(f"Final Calculation ({expected_op})", total_artifact.summary)
        self.assertIn(str(expected_value), total_artifact.summary)

if __name__ == "__main__":
    unittest.main()
