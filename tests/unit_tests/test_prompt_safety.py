import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.decision.manager import Manager
from amnesic.presets.code_agent import MANAGER_SYSTEM_PROMPT

class TestPromptSafety(unittest.TestCase):
    def test_manager_system_prompt_formatting(self):
        """Verify that MANAGER_SYSTEM_PROMPT contains all expected placeholders used by Manager.decide."""
        mock_driver = MagicMock()
        manager = Manager(driver=mock_driver)
        
        session = AmnesicSession(mission="Test Prompt")
        fw_state = session.state['framework_state']
        
        # This will raise KeyError if any {placeholder} is missing from the template
        # or if Manager.decide tries to pass a key that isn't in the template.
        try:
            manager.decide(
                state=fw_state,
                file_map=[],
                pager=session.pager,
                active_context="EMPTY"
            )
        except KeyError as e:
            self.fail(f"MANAGER_SYSTEM_PROMPT is missing mandatory placeholder: {e}")
        except Exception:
            # Other exceptions (like driver mock failing) are fine, 
            # we just care about the .format() call which happens first.
            pass

if __name__ == "__main__":
    unittest.main()
