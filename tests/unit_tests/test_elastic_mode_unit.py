import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.decision.manager import ManagerMove

class TestElasticModeUnit(unittest.TestCase):
    def setUp(self):
        from amnesic.core.sidecar import SharedSidecar
        SharedSidecar().reset()

    def test_elastic_mode_prevents_auto_evict(self):
        """Verify that elastic_mode=True does NOT evict files after save_artifact."""
        session = AmnesicSession(mission="Test", elastic_mode=True)
        session.driver = MagicMock()
        
        # 1. Load a file
        session.pager.request_access("FILE:config_base.py", "BASE_VALUE = 100")
        self.assertIn("FILE:config_base.py", session.pager.active_pages)
        
        # 2. Save an artifact
        with patch('amnesic.decision.worker.Worker.execute_task') as mock_worker:
            mock_worker.return_value = MagicMock(content="100")
            session._tool_worker_task("BASE_VALUE")
            
        # 3. Verify file is STILL in L1
        self.assertIn("FILE:config_base.py", session.pager.active_pages)

    def test_strict_mode_auto_evicts(self):
        """Verify that default (Strict) mode DOES evict files after save_artifact."""
        session = AmnesicSession(mission="Test", elastic_mode=False)
        session.driver = MagicMock()
        
        session.pager.request_access("FILE:hot.py", "content")
        with patch('amnesic.decision.worker.Worker.execute_task') as mock_worker:
            mock_worker.return_value = MagicMock(content="val")
            session._tool_worker_task("hot_artifact")
            
        self.assertNotIn("FILE:hot.py", session.pager.active_pages)

if __name__ == "__main__":
    unittest.main()
