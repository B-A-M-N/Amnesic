import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.decision.manager import ManagerMove

class TestHardeningUnit(unittest.TestCase):
    def setUp(self):
        # Create a temp test dir
        self.root = os.path.abspath("./hardening_jail")
        if not os.path.exists(self.root): os.mkdir(self.root)
        self.session = AmnesicSession(mission="Harden Test", root_dir=self.root)
        self.session.driver = MagicMock()

    def test_path_traversal_blocked(self):
        """Verify that _safe_path raises PermissionError for traversal attempts."""
        bad_paths = [
            "../secret.txt",
            "/etc/passwd",
            "../../.ssh/id_rsa",
            "./../other_dir/file.py"
        ]
        for path in bad_paths:
            with self.subTest(path=path):
                with self.assertRaises(PermissionError):
                    self.session._safe_path(path)

    def test_sensitive_files_blocked(self):
        """Verify that kernel policy blocks access to specific sensitive files."""
        blocked = [".env", ".git/config"]
        for path in blocked:
            with self.subTest(path=path):
                with self.assertRaises(PermissionError):
                    self.session._safe_path(path)

    def test_auditor_physical_preflight(self):
        """Verify that _node_auditor catches security violations BEFORE LLM audit."""
        move = ManagerMove(
            thought_process="I will read your ssh keys now.",
            tool_call="stage_context",
            target="../../../id_rsa"
        )
        
        state = {
            "framework_state": self.session.state['framework_state'],
            "active_file_map": [],
            "manager_decision": move,
            "last_audit": None,
            "last_node": "manager"
        }
        
        # This call should return immediately with REJECT due to Layer 0
        result = self.session._node_auditor(state)
        
        self.assertEqual(result['last_audit']['auditor_verdict'], "REJECT")
        self.assertIn("Path Traversal Blocked", result['last_audit']['rationale'])
        
        # Verify driver was NEVER called (saving tokens/time)
        self.session.driver.generate_structured.assert_not_called()

    def test_multi_root_jail(self):
        """Verify that _safe_path correctly handles multiple allowed roots."""
        root_a = os.path.abspath("./root_a")
        root_b = os.path.abspath("./root_b")
        for d in [root_a, root_b]:
            if not os.path.exists(d): os.mkdir(d)
            
        session = AmnesicSession(mission="Multi Test", root_dir=[root_a, root_b])
        
        # 1. Access inside A
        path_a = os.path.join(root_a, "file.py")
        self.assertEqual(session._safe_path(path_a), path_a)
        
        # 2. Access inside B
        path_b = os.path.join(root_b, "config.json")
        self.assertEqual(session._safe_path(path_b), path_b)
        
        # 3. Access OUTSIDE both
        with self.assertRaises(PermissionError):
            session._safe_path("/etc/passwd")
            
        # Cleanup
        for d in [root_a, root_b]:
            import shutil
            shutil.rmtree(d)

    def test_sandbox_write_redirection(self):
        """Verify that writes go to shadow_fs in sandbox mode."""
        # 1. Init Sandbox Session
        session = AmnesicSession(mission="Sandbox Test", root_dir=self.root, sandbox=True)
        session.driver = MagicMock()
        
        # 2. Setup initial file on disk
        target_file = os.path.join(self.root, "real.py")
        with open(target_file, "w") as f: f.write("x = 1")
        
        # 3. Perform edit via tool (simulating Manager action)
        # We need to mock the Worker to return the diff
        from amnesic.decision.worker import CodeEdit
        with unittest.mock.patch('amnesic.decision.worker.Worker.perform_edit') as mock_worker:
            mock_worker.return_value = CodeEdit(
                original_snippet="x = 1", 
                new_snippet="x = 99", 
                verification_notes="Test"
            )
            
            # Execute edit
            session._tool_edit(f"{target_file}: change 1 to 99")
            
        # 4. Verify Disk is UNTOUCHED
        with open(target_file, "r") as f: content = f.read()
        self.assertEqual(content, "x = 1")
        
        # 5. Verify Shadow FS has CHANGE
        self.assertIn(target_file, session.shadow_fs)
        self.assertEqual(session.shadow_fs[target_file], "x = 99")

    def tearDown(self):
        if os.path.exists(self.root):
            import shutil
            shutil.rmtree(self.root)

if __name__ == "__main__":
    unittest.main()
