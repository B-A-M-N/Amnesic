import unittest
from unittest.mock import MagicMock
from amnesic.decision.auditor import Auditor, PROFILE_MAP
from amnesic.core.audit_policies import FLUID_READ

class TestAuditPolicies(unittest.TestCase):
    def setUp(self):
        self.mock_driver = MagicMock()
        self.goal = "Analyze the codebase."
        self.constraints = []
        
        # Initialize Auditor with FLUID_READ profile
        self.auditor = Auditor(
            goal=self.goal, 
            constraints=self.constraints, 
            driver=self.mock_driver, 
            audit_profile=FLUID_READ
        )

    def test_fluid_read_fast_path(self):
        """Verify that FLUID_READ skips LLM for stage_context."""
        action = "stage_context"
        target = "src/main.py"
        rationale = "I need to read the main entry point to understand the flow."
        
        # Mock valid files so existence check passes
        valid_files = ["src/main.py"]
        
        # Mock embedding logic to force high relevance
        # We need to mock _check_relevance or the embedder itself
        # Easier to mock _check_relevance since we aren't testing the embedding model here
        self.auditor._check_relevance = MagicMock(return_value=0.95)
        
        result = self.auditor.evaluate_move(
            action_type=action,
            target=target,
            manager_rationale=rationale,
            valid_files=valid_files
        )
        
        # Assertions
        self.assertEqual(result["auditor_verdict"], "PASS")
        self.assertEqual(result["confidence_score"], 1.0)
        self.assertIn("Fast-Path Approved", result["rationale"])
        
        # KEY: Ensure LLM was NOT called
        self.mock_driver.generate_structured.assert_not_called()

    def test_strict_action_forces_audit(self):
        """Verify that write_file ALWAYS triggers LLM audit even in FLUID_READ."""
        action = "write_file"
        target = "src/new_feature.py"
        rationale = "Writing new code."
        
        # High relevance, but action is STRICT
        self.auditor._check_relevance = MagicMock(return_value=0.95)
        
        # Mock LLM response for the mandatory check
        mock_verdict = MagicMock()
        mock_verdict.outcome = "PASS"
        mock_verdict.rationale = "LLM Approved"
        mock_verdict.correction = None
        self.mock_driver.generate_structured.return_value = mock_verdict
        
        # Mock valid user files for L1 check
        active_pages = ["src/main.py"]
        
        result = self.auditor.evaluate_move(
            action_type=action,
            target=target,
            manager_rationale=rationale,
            active_pages=active_pages,
            active_context="some context"
        )
        
        # KEY: Ensure LLM WAS called
        self.mock_driver.generate_structured.assert_called_once()
        self.assertEqual(result["auditor_verdict"], "PASS")

    def test_irrelevant_fast_path_fails(self):
        """Verify that Fast Path is rejected if relevance is too low."""
        action = "stage_context"
        target = "random_garbage.txt"
        rationale = "Just looking around."
        
        valid_files = ["random_garbage.txt"]
        
        # Relevance below threshold (0.10 for FLUID_READ fast path)
        self.auditor._check_relevance = MagicMock(return_value=0.01)
        
        result = self.auditor.evaluate_move(
            action_type=action,
            target=target,
            manager_rationale=rationale,
            valid_files=valid_files
        )
        
        self.assertEqual(result["auditor_verdict"], "REJECT")
        self.assertIn("Irrelevant action", result["rationale"])
        self.mock_driver.generate_structured.assert_not_called()

if __name__ == '__main__':
    unittest.main()
