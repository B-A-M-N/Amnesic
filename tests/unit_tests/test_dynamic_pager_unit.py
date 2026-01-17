import unittest
from amnesic.core.dynamic_pager import DynamicPager, DynamicPage

class TestDynamicPager(unittest.TestCase):
    def setUp(self):
        self.pager = DynamicPager(capacity_tokens=50)

    def test_ttl_eviction(self):
        # Load a page
        self.pager.request_access("page1", "content")
        page = self.pager.active_pages["page1"]
        self.assertEqual(page.ttl, 10)
        
        # Tick 9 times
        for _ in range(9):
            self.pager.tick()
        self.assertEqual(page.ttl, 1)
        self.assertIn("page1", self.pager.active_pages)
        
        # 10th tick -> Eviction
        self.pager.tick()
        self.assertNotIn("page1", self.pager.active_pages)
        self.assertIn("page1", self.pager.swap_disk) # L2

    def test_ttl_reset_on_access(self):
        self.pager.request_access("page1", "content")
        self.pager.tick()
        page = self.pager.active_pages["page1"]
        self.assertEqual(page.ttl, 9)
        
        # Access again
        self.pager.request_access("page1")
        self.assertEqual(page.ttl, 10)

    def test_lru_eviction(self):
        # Capacity 100. 
        # "a" * 150 -> ~50 tokens (150/3)
        large_content = "a" * 150 
        
        self.pager.request_access("page1", large_content)
        self.pager.tick() # turn 1
        
        self.pager.request_access("page2", large_content)
        self.pager.tick() # turn 2
        
        # Now both fit (approx 50+50=100).
        self.assertIn("page1", self.pager.active_pages)
        self.assertIn("page2", self.pager.active_pages)
        
        # Access page1 to make it recent
        self.pager.request_access("page1") 
        
        # Load page3. Needs 50 tokens. Must evict.
        # page2 was accessed at turn 1 (creation). page1 accessed at turn 2 (refresh).
        # page2 is LRU.
        self.pager.request_access("page3", large_content)
        
        self.assertNotIn("page2", self.pager.active_pages)
        self.assertIn("page1", self.pager.active_pages)
        self.assertIn("page3", self.pager.active_pages)

    def test_current_turn_increment(self):
        self.assertEqual(self.pager.current_turn, 0)
        self.pager.tick()
        self.assertEqual(self.pager.current_turn, 1)

if __name__ == "__main__":
    unittest.main()
