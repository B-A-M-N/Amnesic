import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.core.sidecar import SharedSidecar
from amnesic.presets.code_agent import Artifact

class TestCapabilities(unittest.TestCase):
    def setUp(self):
        self.session = AmnesicSession(mission="Cap Test", l1_capacity=3000)
        self.session.driver = MagicMock()
        self.session.manager_node.driver = self.session.driver
        # Mock Environment to avoid FS
        self.session.env = MagicMock()
        self.session.env.refresh_substrate.return_value = []

    def test_cap_1_garbage_collection(self):
        """Verify that _tool_worker_task triggers eviction (Context GC)."""
        # 1. Setup L1 with a file
        self.session.pager.request_access("FILE:heavy_data.py", "DATA_BLOB = [...]")
        self.assertIn("FILE:heavy_data.py", self.session.pager.active_pages)
        
        # 2. Execute Worker Task (Extract)
        with patch('amnesic.decision.worker.Worker.execute_task') as mock_worker:
            mock_worker.return_value = MagicMock(content="[...] 100 numbers")
            self.session._tool_worker_task("heavy_data_blob")
            
        # 3. Verify Eviction happened
        self.assertNotIn("FILE:heavy_data.py", self.session.pager.active_pages)
        # Verify Artifact created
        arts = self.session.state['framework_state'].artifacts
        self.assertTrue(any(a.identifier == "heavy_data_blob" for a in arts))

    def test_cap_2_time_travel(self):
        """Verify snapshot_state and restore_state mechanism."""
        # 1. Add artifact
        self.session.state['framework_state'].artifacts.append(
            Artifact(identifier="calc_logic", type="text_content", summary="def add(a,b): return a - b", status="staged")
        )
        
        # 2. Snapshot
        snap_id = self.session.snapshot_state("buggy_state")
        
        # 3. Modify state (Fix bug)
        self.session.state['framework_state'].artifacts = []
        
        # 4. Restore
        self.session.restore_state(snap_id)
        
        # 5. Verify restoration
        arts = self.session.state['framework_state'].artifacts
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0].identifier, "calc_logic")

    def test_cap_5_hive_mind(self):
        """Verify SharedSidecar synchronization."""
        # 1. Setup Shared Sidecar
        shared = SharedSidecar()
        shared.reset()
        self.session.sidecar = shared
        
        # 2. Ingest Data via Worker Task
        with patch('amnesic.decision.worker.Worker.execute_task') as mock_worker:
            mock_worker.return_value = MagicMock(content="Glory to the Graph")
            self.session._tool_worker_task("PROTOCOL_OMEGA")
            
        # 3. Verify Sidecar has it
        self.assertEqual(shared.query_knowledge("PROTOCOL_OMEGA"), "Glory to the Graph")
        
        # 4. Verify another session can see it
        session_b = AmnesicSession(sidecar=shared)
        # Manually trigger manager node logic to check injection
        # (Mocking env/driver for B as well)
        session_b.env = MagicMock()
        session_b.env.refresh_substrate.return_value = []
        session_b.driver = MagicMock()
        session_b.manager_node.driver = session_b.driver
        
        # Run node manager (should inject artifacts)
        state_b = {
            "framework_state": session_b.state['framework_state'],
            "active_file_map": [],
            "manager_decision": None
        }
        session_b.graph._node_manager(state_b)
        
        arts_b = session_b.state['framework_state'].artifacts
        self.assertTrue(any(a.identifier == "PROTOCOL_OMEGA" and "Glory to the Graph" in a.summary for a in arts_b))

    def test_cap_6_isolation(self):
        """Verify that _tool_edit performs edits on the file system (simulated)."""
        # This tests the tool logic, assuming Worker returns a diff
        with patch('amnesic.decision.worker.Worker.perform_edit') as mock_edit, \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data="SYSTEM_STATUS = 'ONLINE'")) as mock_file:
            
            # Setup Edit result
            mock_edit.return_value = MagicMock(original_snippet="'ONLINE'", new_snippet="'CRITICAL FAILURE'")
            
            # Execute
            self.session._tool_edit("stable_core.py: set to CRITICAL FAILURE")
            
            # Verify write occurred (simplified check)
            self.assertTrue(mock_file.called)

    def test_cap_9_ignorance(self):
        """Verify that staging a missing file returns a CRITICAL ERROR feedback."""
        with patch('os.path.exists', return_value=False):
            self.session._tool_stage("legacy_db.py")
            
        feedback = self.session.state['framework_state'].last_action_feedback
        self.assertIn("CRITICAL ERROR", feedback)
        self.assertIn("legacy_db.py", feedback)
        self.assertIn("NOT FOUND", feedback)

if __name__ == "__main__":
    unittest.main()
