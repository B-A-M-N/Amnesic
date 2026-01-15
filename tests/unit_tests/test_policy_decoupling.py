import os
import sys
import unittest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.core.policies import KernelPolicy, DEFAULT_COMPLETION_POLICY

class TestPolicyDecoupling(unittest.TestCase):
    def test_default_policies_enabled(self):
        print("\nTesting Default Policies Enabled...")
        session = AmnesicSession(mission="Test", use_default_policies=True)
        # Check if DEFAULT_COMPLETION_POLICY is present by name
        policy_names = [p.name for p in session.manager_node.policies]
        self.assertIn("LegacyMissionComplete", policy_names)
        self.assertIn("CriticalErrorHalt", policy_names)
        print("PASS: Defaults present.")

    def test_default_policies_disabled(self):
        print("\nTesting Default Policies Disabled...")
        session = AmnesicSession(mission="Test", use_default_policies=False)
        policy_names = [p.name for p in session.manager_node.policies]
        self.assertNotIn("LegacyMissionComplete", policy_names)
        self.assertNotIn("CriticalErrorHalt", policy_names)
        self.assertEqual(len(policy_names), 0)
        print("PASS: Defaults absent.")

    def test_custom_policy_injection(self):
        print("\nTesting Custom Policy Injection...")
        
        def dummy_condition(state): return False
        def dummy_reaction(state): return None
        
        custom_policy = KernelPolicy(name="CustomTestPolicy", condition=dummy_condition, reaction=dummy_reaction)
        
        session = AmnesicSession(mission="Test", use_default_policies=False, policies=[custom_policy])
        policy_names = [p.name for p in session.manager_node.policies]
        
        self.assertIn("CustomTestPolicy", policy_names)
        self.assertEqual(len(policy_names), 1)
        print("PASS: Custom policy injected correctly.")

if __name__ == "__main__":
    unittest.main()
