import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.decision.worker import Worker, GenerationArtifact, CodeEdit

class TestWorkerTypesRegression(unittest.TestCase):
    def setUp(self):
        self.mock_driver = MagicMock()
        self.worker = Worker(self.mock_driver)

    def test_extraction_worker_intent_recovery(self):
        """Regression: Ensure Extraction Worker uses Intent Recovery instructions."""
        # We check if the system prompt contains the required "lying variables" instructions
        with patch.object(self.mock_driver, 'generate_structured') as mock_gen:
            self.worker.execute_task(
                task_description="Extract VAL_A",
                active_context="not_val_a = 42",
                constraints=["Raw value only"]
            )
            
            call_args = mock_gen.call_args
            system_prompt = call_args.kwargs['system_prompt']
            self.assertIn("intentionally misleading (lying)", system_prompt)
            self.assertIn("Recover the INTENT", system_prompt)

    def test_edit_worker_surgical_precision(self):
        """Regression: Ensure Edit Worker receives target file and instructions correctly."""
        with patch.object(self.mock_driver, 'generate_structured') as mock_gen:
            self.worker.perform_edit(
                target_file="app.py",
                instructions="Change 0.5 to 0.05",
                active_context="rate = 0.5",
                constraints=["Indent preservation"]
            )
            
            call_args = mock_gen.call_args
            user_prompt = call_args.kwargs['user_prompt']
            self.assertIn("TARGET FILE: app.py", user_prompt)
            self.assertIn("INSTRUCTIONS: Change 0.5 to 0.05", user_prompt)
            self.assertIn("rate = 0.5", user_prompt)

    def test_generation_artifact_validation(self):
        """Regression: Ensure GenerationArtifact handles 1MB payload limit."""
        # Valid size
        small_artifact = GenerationArtifact(content="safe", verification_notes="ok")
        self.assertEqual(small_artifact.content, "safe")
        
        # Invalid size (OOM Protection)
        with self.assertRaises(ValueError) as cm:
            GenerationArtifact(content="X" * 1_000_001)
        self.assertIn("Physical Payload Limit Exceeded", str(cm.exception))

    def test_code_edit_validation(self):
        """Regression: Ensure CodeEdit handles 1MB payload limit."""
        with self.assertRaises(ValueError) as cm:
            CodeEdit(original_snippet="old", new_snippet="X" * 1_000_001)
        self.assertIn("Physical Payload Limit Exceeded", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
