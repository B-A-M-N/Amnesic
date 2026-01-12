import unittest
import sys
import os
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.drivers.ollama import OllamaDriver
from amnesic.presets.code_agent import ManagerMove

class TestJSONHealingRegression(unittest.TestCase):
    def setUp(self):
        # We don't need a real model for these static parsing tests
        self.driver = OllamaDriver(model_name="dummy")

    def test_heal_markdown_and_thinking(self):
        """Regression: Ensure driver strips <think> tags and markdown fences."""
        raw_output = """
<think>
I need to stage the file.
</think>
```json
{
  "thought_process": "Backpack: [None]. L1 empty. Staging api.py.",
  "tool_call": "stage_context",
  "target": "api.py"
}
```
"""
        result = self.driver._extract_json_block(raw_output, ManagerMove)
        self.assertIsNotNone(result)
        self.assertEqual(result.tool_call, "stage_context")
        self.assertEqual(result.target, "api.py")

    def test_heal_key_value_fallback(self):
        """Regression: Ensure driver handles semi-structured KV pairs from smaller models."""
        raw_output = """
THOUGHT PROCESS: I need to save the value now.
TOOL CALL: save_artifact
TARGET: X_value
"""
        result = self.driver._extract_json_block(raw_output, ManagerMove)
        self.assertIsNotNone(result)
        self.assertEqual(result.tool_call, "save_artifact")
        self.assertEqual(result.target, "X_value")

    def test_heal_direct_tool_call(self):
        """Regression: Ensure driver handles models trying to call tools like a CLI."""
        raw_output = "stage_context('island_a.txt')"
        result = self.driver._extract_json_block(raw_output, ManagerMove)
        self.assertIsNotNone(result)
        self.assertEqual(result.tool_call, "stage_context")
        self.assertEqual(result.target, "island_a.txt")

    def test_heal_malformed_json_quotes(self):
        """Regression: Ensure driver heals single quotes and Python-style booleans."""
        raw_output = "{'thought_process': 'Testing', 'tool_call': 'halt_and_ask', 'target': 'Done', 'status': True}"
        # We use a dummy schema that matches this
        class DummySchema(BaseModel):
            thought_process: str
            tool_call: str
            target: str

        result = self.driver._extract_json_block(raw_output, DummySchema)
        self.assertIsNotNone(result)
        self.assertEqual(result.tool_call, "halt_and_ask")

    def test_heal_wrapped_edit_file(self):
        """Regression: Handle models that provide content in a separate field."""
        raw_output = """
THOUGHT: Fixing the bug.
TOOL CALL: edit_file
TARGET: app.py
CONTENT: return 0.05
"""
        result = self.driver._extract_json_block(raw_output, ManagerMove)
        self.assertIsNotNone(result)
        self.assertEqual(result.tool_call, "edit_file")
        self.assertIn("app.py: return 0.05", result.target)

if __name__ == "__main__":
    unittest.main()
