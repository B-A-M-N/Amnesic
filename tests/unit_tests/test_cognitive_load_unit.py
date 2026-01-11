import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.dynamic_pager import DynamicPager

class TestCognitiveLoadUnit(unittest.TestCase):
    def setUp(self):
        self.pager = DynamicPager(capacity_tokens=100)

    def test_rejection_of_oversized_file(self):
        """Verify that a file larger than L1 capacity is rejected."""
        # 100 tokens = 400 chars roughly. 
        large_content = "X" * 1000 # 250 tokens
        
        success = self.pager.request_access("FILE:too_big.py", large_content)
        
        self.assertFalse(success)
        self.assertNotIn("FILE:too_big.py", self.pager.l1_active)
        # It should however be in L2 (as a safety swap)
        self.assertIn("FILE:too_big.py", self.pager.l2_staging)

    def test_eviction_on_load(self):
        """Verify that loading a new file evicts old ones to fit."""
        self.pager.request_access("FILE:small_1.py", "X" * 200, priority=5) # 50 tokens
        self.assertEqual(self.pager.current_usage, 50)
        
        self.pager.tick() # Advance time
        
        self.pager.request_access("FILE:small_2.py", "Y" * 300, priority=5) # 75 tokens
        # 50 + 75 = 125 > 100. small_1 should be evicted.
        
        self.assertIn("FILE:small_2.py", self.pager.l1_active)
        self.assertNotIn("FILE:small_1.py", self.pager.l1_active)
        self.assertIn("FILE:small_1.py", self.pager.l2_staging)
        self.assertEqual(self.pager.current_usage, 75)

if __name__ == "__main__":
    unittest.main()
