import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession

class TestPersonaSwap(unittest.TestCase):
    def setUp(self):
        self.session = AmnesicSession(
            mission="Swap Test", 
            l1_capacity=1500,
            strategy="Original Strategy"
        )
        self.session.driver = MagicMock()
        self.session.env = MagicMock()
        self.session.env.refresh_substrate.return_value = []

    def test_switch_strategy_updates_state(self):
        """Verify that switch_strategy updates the framework state."""
        # Check initial state
        self.assertEqual(self.session.state['framework_state'].strategy, "Original Strategy")
        
        # Execute tool
        self.session._tool_switch_strategy("New Strategy")
        
        # Check updated state
        self.assertEqual(self.session.state['framework_state'].strategy, "New Strategy")
        self.assertIn("Strategy: New Strategy", self.session.state['framework_state'].last_action_feedback)

if __name__ == "__main__":
    unittest.main()
