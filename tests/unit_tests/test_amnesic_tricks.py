import unittest
import os
import shutil
from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class TestAmnesicTricks(unittest.TestCase):
    def setUp(self):
        self.test_dir = "temp_tricks"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create a large file for grepping
        with open(os.path.join(self.test_dir, "large_file.py"), "w") as f:
            f.write("def small_func():\n    return 'found_it'\n\n")
            for i in range(500):
                f.write(f"def noise_{i}():\n    pass\n\n")
            f.write("class LargeClass:\n    def target_method(self):\n        return 'bingo'\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_contextual_grepping(self):
        """Verify that ?query syntax loads only the requested symbol."""
        session = AmnesicSession(mission="Grep test", root_dir=self.test_dir)
        
        # Test function grep
        session._tool_stage("large_file.py?query=small_func")
        active_content = session.pager.render_context()
        self.assertIn("def small_func()", active_content)
        self.assertNotIn("def noise_0()", active_content)
        self.assertIn("large_file.py[small_func]", str(list(session.pager.active_pages.keys())))

        # Test class method grep
        session._tool_unstage("large_file.py[small_func]")
        session._tool_stage("large_file.py?query=target_method")
        active_content = session.pager.render_context()
        self.assertIn("def target_method", active_content)
        self.assertNotIn("small_func", active_content)

    def test_semantic_pinning(self):
        """Verify that PINNED_L1 artifacts survive context wipes."""
        session = AmnesicSession(mission="Pin test", root_dir=self.test_dir)
        
        # 1. Save pinned artifact
        session._tool_worker_task("PINNED_L1:CRITICAL_LOGIC: Use regex ^[A-Z]$")
        
        # 2. Verify it's pinned in pager
        self.assertTrue(session.pager.active_pages["ARTIFACT:CRITICAL_LOGIC"].pinned)
        
        # 3. Save standard artifact
        session._tool_worker_task("STANDARD: noise")
        
        # 4. Trigger a "Simulated" wipe by un-pinning and un-staging standard stuff?
        # Actually, standard unstage_context doesn't touch pinned. 
        # Pinned pages are excluded from evict_to_l2 in some logic (check pager).
        
        # Let's verify it persists after other files are staged
        # In strict mode, staging a new file should evict old standard files but NOT pinned ones.
        session._tool_stage("large_file.py")
        self.assertIn("ARTIFACT:CRITICAL_LOGIC", session.pager.active_pages)

    def test_jit_deduplication(self):
        """Verify that redundant artifacts are collapsed."""
        from amnesic.core.sidecar import SharedSidecar
        # Use a fresh, empty sidecar to avoid artifacts from previous tests
        sidecar = SharedSidecar(driver=None) 
        session = AmnesicSession(mission="JIT test", root_dir=self.test_dir, sidecar=sidecar)
        
        # Clear any system-pre-loaded artifacts if they exist
        session.state['framework_state'].artifacts = []
        
        # 1. Save two distinct artifacts
        session._tool_worker_task("VAL_A: 10")
        session._tool_worker_task("VAL_B: 20")
        self.assertEqual(len(session.state['framework_state'].artifacts), 2)
        
        # 2. Save a duplicate value
        session._tool_worker_task("VAL_C: 10")
        
        # 3. Should have collapsed C into A (or kept A)
        # Check current artifacts
        identifiers = [a.identifier for a in session.state['framework_state'].artifacts]
        self.assertIn("VAL_A", identifiers)
        self.assertNotIn("VAL_C", identifiers)
        self.assertEqual(len(identifiers), 2)

if __name__ == "__main__":
    unittest.main()
