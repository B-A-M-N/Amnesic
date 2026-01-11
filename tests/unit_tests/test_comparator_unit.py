import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.dynamic_pager import DynamicPager
from amnesic.core.comparator import Comparator

class TestComparatorUnit(unittest.TestCase):
    def setUp(self):
        self.pager = DynamicPager(capacity_tokens=1000)
        self.comparator = Comparator(self.pager)

    def test_load_pair_success(self):
        """Verify that load_pair successfully loads two files into L1."""
        file_a = "file_a.py"
        content_a = "content a"
        file_b = "file_b.py"
        content_b = "content b"
        
        success = self.comparator.load_pair(file_a, content_a, file_b, content_b)
        
        self.assertTrue(success)
        self.assertIn(f"FILE:{file_a}", self.pager.l1_active)
        self.assertIn(f"FILE:{file_b}", self.pager.l1_active)

    def test_load_pair_oom(self):
        """Verify that load_pair fails and cleans up if files exceed capacity."""
        # Reset capacity to very small
        self.pager.capacity = 10
        file_a = "large_a.py"
        content_a = "this is a very long string that will exceed ten tokens easily"
        
        success = self.comparator.load_pair(file_a, content_a, "b.py", "b")
        
        self.assertFalse(success)
        self.assertNotIn(f"FILE:{file_a}", self.pager.l1_active)
        self.assertEqual(len(self.pager.l1_active), 0)

    def test_purge_pair(self):
        """Verify that purge_pair removes the files from L1."""
        file_a = "a.py"
        file_b = "b.py"
        self.comparator.load_pair(file_a, "a", file_b, "b")
        
        self.comparator.purge_pair()
        
        self.assertNotIn(f"FILE:{file_a}", self.pager.l1_active)
        self.assertNotIn(f"FILE:{file_b}", self.pager.l1_active)

if __name__ == "__main__":
    unittest.main()
