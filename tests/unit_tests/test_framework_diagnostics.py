import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import FrameworkState, Artifact
from amnesic.core.memory import compress_history

class TestFrameworkDiagnostics(unittest.TestCase):
    def setUp(self):
        # We mock driver to avoid any network/ollama calls
        self.mock_driver = MagicMock()
        
    def test_invalid_provider_raises_error(self):
        """Verify that AmnesicSession raises a clear error for unsupported providers."""
        with self.assertRaises(ValueError) as cm:
            AmnesicSession(mission="Test", provider="unsupported_ai")
        self.assertIn("Unknown provider", str(cm.exception))

    def test_custom_tool_registration(self):
        """Verify that a user can register and execute a custom tool."""
        session = AmnesicSession(mission="Custom Tool Test")
        
        # Define a custom tool
        def my_custom_tool(target: str):
            return f"Processed {target}"
        
        session.tools.register_tool("my_custom_tool", my_custom_tool)
        
        # Verify tool is in registry
        self.assertIn("my_custom_tool", session.tools.get_tool_names())
        
        # Execute tool through registry
        result = session.tools.execute("my_custom_tool", target="data")
        self.assertEqual(result, "Processed data")

    def test_state_serialization(self):
        """Verify that FrameworkState can be serialized to a dict and back."""
        state = FrameworkState(
            task_intent="Test Serialization",
            current_hypothesis="Working",
            confidence_score=0.8,
            artifacts=[
                Artifact(identifier="A1", type="text_content", summary="Data", status="staged")
            ]
        )
        
        # Convert to dict (Pydantic model_dump)
        state_dict = state.model_dump()
        
        # Verify dict content
        self.assertEqual(state_dict["task_intent"], "Test Serialization")
        self.assertEqual(len(state_dict["artifacts"]), 1)
        self.assertEqual(state_dict["artifacts"][0]["identifier"], "A1")
        
        # Reconstruct from dict
        new_state = FrameworkState(**state_dict)
        self.assertEqual(new_state.task_intent, state.task_intent)
        self.assertEqual(new_state.confidence_score, state.confidence_score)
        self.assertEqual(len(new_state.artifacts), 1)

    def test_history_compression_logic(self):
        """Verify that history compression collapses old turns correctly."""
        # Use more than 10 turns to trigger cutoff in memory.py
        history = [f"Turn {i}: Action -> PASS" for i in range(15)]
        
        compressed = compress_history(history, max_turns=5)
        
        # Should have a Milestone line
        self.assertIn("MILESTONE: Successfully processed", compressed)
        # Should have the last few turns
        self.assertIn("Turn 14: Action", compressed)
        self.assertIn("Turn 13: Action", compressed)
        # Should NOT have the first turn (Turn 0)
        self.assertNotIn("Turn 0: Action", compressed)

    def test_session_init_with_missing_root_dir(self):
        """Verify behavior when root_dir is invalid (Environment handles it usually)."""
        # ExecutionEnvironment just sets the path, it doesn't strictly validate existence on init
        # but let's check if it handles it gracefully.
        session = AmnesicSession(mission="Test", root_dir="/non/existent/path/9999")
        self.assertEqual(session.env.root_dirs, ["/non/existent/path/9999"])
        
        # Scan should return empty list without crashing
        repo_map = session.env.refresh_substrate()
        self.assertEqual(repo_map, [])

if __name__ == "__main__":
    unittest.main()
