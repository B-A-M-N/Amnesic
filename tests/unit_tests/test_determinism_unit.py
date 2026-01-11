import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession

class TestDeterminismUnit(unittest.TestCase):
    @patch('amnesic.core.session.get_driver')
    def test_deterministic_seed_sets_temperature(self, mock_get_driver):
        """Verify that deterministic_seed=True sets temperature to 0.0 in driver."""
        AmnesicSession(mission="Test", deterministic_seed=42)
        
        # Check call args of get_driver
        args, kwargs = mock_get_driver.call_args
        self.assertEqual(kwargs.get("temperature"), 0.0)

    @patch('amnesic.core.session.get_driver')
    def test_no_seed_uses_default_temperature(self, mock_get_driver):
        """Verify that omitting seed doesn't force temperature to 0.0 (uses factory default)."""
        AmnesicSession(mission="Test")
        
        args, kwargs = mock_get_driver.call_args
        self.assertIsNone(kwargs.get("temperature")) # Factory handles default

if __name__ == "__main__":
    unittest.main()
