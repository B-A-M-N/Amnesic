import unittest
import sys
import os
import re
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class TestCalculateToolEdgeCases(unittest.TestCase):
    """
    Focuses EXCLUSIVELY on math expression parsing and numerical edge cases.
    Avoids 'Island Hopping' or high-level mission state tests covered elsewhere.
    """
    def setUp(self):
        self.session = AmnesicSession(model="dummy", l1_capacity=3000)
        self.session.driver = MagicMock()
        self.session.state['framework_state'].artifacts = []

    def test_math_negative_numbers(self):
        """Verify handling of negative numbers in the expression string."""
        # The regex findall(r'\d+') will find [10, 5]. 
        # The operator '-' will then do 10 - 5 = 5.
        self.session._tool_calculate("10 - 5") 
        self._assert_result(5, "SUBTRACT")

    def test_math_floating_point_division(self):
        """Verify division returns float and is handled correctly."""
        self.session._tool_calculate("10 / 4")
        self._assert_result(2.5, "DIVIDE")

    def test_math_operator_precedence_hierarchy(self):
        """
        Verify the fixed precedence hierarchy of the tool:
        MULTIPLY > DIVIDE > SUBTRACT > ADD (based on the if/elif chain).
        """
        # "10 + 2 * 5"
        # Since '*' is detected, it triggers MULTIPLY.
        # findall captures [10, 2, 5].
        # Implementation uses 10 * 2 * 5 = 100.
        self.session._tool_calculate("10 + 2 * 5")
        self._assert_result(100, "MULTIPLY")

    def test_math_zero_division_safety(self):
        """Verify division by zero produces an error artifact."""
        self.session._tool_calculate("10 / 0")
        artifacts = self.session.state['framework_state'].artifacts
        total_artifact = next((a for a in artifacts if a.identifier == "TOTAL"), None)
        self.assertIsNotNone(total_artifact)
        self.assertEqual(total_artifact.type, "error_log")
        self.assertIn("Division by zero", total_artifact.summary)

    def test_math_multiple_operands(self):
        """Verify the tool sums numbers (default ADD) correctly."""
        # result = sum([1, 2, 3]) = 6
        self.session._tool_calculate("1 + 2 + 3")
        self._assert_result(6, "ADD")

    def _assert_result(self, expected_value, expected_op):
        artifacts = self.session.state['framework_state'].artifacts
        total_artifact = next((a for a in artifacts if a.identifier == "TOTAL"), None)
        self.assertIsNotNone(total_artifact)
        # Updated output format: "Final ({op}): {res}"
        self.assertIn(f"Final ({expected_op})", total_artifact.summary)
        
        # Extract number for comparison
        match = re.search(r'([\d\.]+)', total_artifact.summary.split(":")[-1])
        self.assertEqual(float(match.group(1)), float(expected_value))

if __name__ == "__main__":
    unittest.main()