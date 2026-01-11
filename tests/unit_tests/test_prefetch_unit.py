import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.core.dynamic_pager import DynamicPager

class TestPrefetchUnit(unittest.TestCase):
    def setUp(self):
        self.pager = DynamicPager(capacity_tokens=1000)

    def test_prefetch_loads_to_l2(self):
        """Verify that prefetch loads content into L2 and NOT L1."""
        page_id = "FILE:background.py"
        content = "print('hello')"
        
        self.pager.prefetch(page_id, content)
        
        # Verify L2 has it
        self.assertIn(page_id, self.pager.l2_staging)
        # Verify L1 does NOT have it
        self.assertNotIn(page_id, self.pager.l1_active)
        # Verify content
        self.assertEqual(self.pager.l2_staging[page_id].content, content)

    def test_prefetch_does_not_overwrite_l1(self):
        """Verify that prefetch does nothing if page is already in L1."""
        page_id = "FILE:hot.py"
        content_l1 = "original"
        content_prefetch = "new"
        
        self.pager.request_access(page_id, content_l1)
        self.assertIn(page_id, self.pager.l1_active)
        
        self.pager.prefetch(page_id, content_prefetch)
        
        # Verify L1 still has original
        self.assertEqual(self.pager.l1_active[page_id].content, content_l1)
        # Verify L2 is empty
        self.assertNotIn(page_id, self.pager.l2_staging)

    def test_prefetch_updates_l2(self):
        """Verify that prefetch updates an existing L2 page."""
        page_id = "FILE:swap.py"
        self.pager.prefetch(page_id, "v1")
        self.assertEqual(self.pager.l2_staging[page_id].content, "v1")
        
        self.pager.prefetch(page_id, "v2")
        self.assertEqual(self.pager.l2_staging[page_id].content, "v2")

if __name__ == "__main__":
    unittest.main()
