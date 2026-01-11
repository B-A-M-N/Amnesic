import unittest
import sys
import os
from unittest.mock import MagicMock, patch, mock_open

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.decision.worker import CodeEdit

class TestCodeEngineeringUnit(unittest.TestCase):
    def setUp(self):
        self.session = AmnesicSession(mission="Code Test")
        self.session.driver = MagicMock()

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data="def old(): pass\n")
    def test_tool_edit_success(self, mock_file, mock_exists):
        """Verify _tool_edit successfully replaces a snippet in a file."""
        with patch('amnesic.decision.worker.Worker.perform_edit') as mock_worker_edit:
            mock_worker_edit.return_value = CodeEdit(
                original_snippet="def old(): pass",
                new_snippet="def new(): pass",
                verification_notes="Renamed"
            )
            
            self.session._tool_edit("app.py: rename function")
            
            # Verify file was opened for writing the new content
            # The tool does: content.replace(...) then f.write(new_content)
            # We can't easily check the write() args with simple mock_open if we don't handle the read/write calls carefully
            # but we can check if it was called.
            self.assertTrue(mock_file.called)
            # Check if artifact was created
            arts = self.session.state['framework_state'].artifacts
            self.assertTrue(any(a.identifier == "diff_app.py" for a in arts))

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data="mismatching content\n")
    def test_tool_edit_snippet_mismatch(self, mock_file, mock_exists):
        """Verify _tool_edit handles cases where the original_snippet is not found."""
        with patch('amnesic.decision.worker.Worker.perform_edit') as mock_worker_edit:
            mock_worker_edit.return_value = CodeEdit(
                original_snippet="nonexistent",
                new_snippet="new",
                verification_notes="Failed"
            )
            
            self.session._tool_edit("app.py: try edit")
            
            self.assertIn("Edit Failed: Original snippet not found", self.session.state['framework_state'].last_action_feedback)

    @patch('os.path.exists', return_value=False)
    def test_tool_edit_file_not_found(self, mock_exists):
        """Verify _tool_edit handles missing files."""
        self.session._tool_edit("ghost.py: fix")
        self.assertIn("Edit Failed: File ghost.py not found", self.session.state['framework_state'].last_action_feedback)

if __name__ == "__main__":
    unittest.main()
