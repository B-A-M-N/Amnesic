import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.presets.clean_room import CleanRoomSession
from amnesic.presets.rosetta import RosettaSession
from amnesic.presets.mediator import MediatorSession
from amnesic.presets.code_agent import Artifact

class TestPresetsUnit(unittest.TestCase):
    def test_clean_room_hygiene(self):
        """Verify CleanRoomSession.verify_hygiene detects leaks."""
        session = CleanRoomSession(mission="Test")
        
        # 1. Setup artifacts (one clean, one leaked)
        session.state['framework_state'].artifacts = [
            Artifact(identifier="A1", type="text_content", summary="REDACTED_KEY", status="staged"),
            Artifact(identifier="A2", type="text_content", summary="sk-LIVE-1234", status="staged")
        ]
        
        # 2. Verify leaks detected
        is_clean = session.verify_hygiene(["sk-LIVE"])
        self.assertFalse(is_clean)
        
        # 3. Verify clean session passes
        session.state['framework_state'].artifacts = [
            Artifact(identifier="A1", type="text_content", summary="REDACTED_KEY", status="staged")
        ]
        is_clean = session.verify_hygiene(["sk-LIVE"])
        self.assertTrue(is_clean)

    def test_rosetta_mission_injection(self):
        """Verify RosettaSession injects migration constraints into mission."""
        session = RosettaSession(mission="Migrate stuff")
        self.assertIn("MIGRATION PROTOCOL ACTIVE", session.mission)
        self.assertIn("ROSETTA TRANSLATOR", session.mission)

    def test_mediator_mission_injection(self):
        """Verify MediatorSession injects conflict resolution constraints into mission."""
        session = MediatorSession(mission="Resolve conflict")
        self.assertIn("CONFLICT RESOLUTION PROTOCOL ACTIVE", session.mission)
        self.assertIn("compare_files", session.mission)

if __name__ == "__main__":
    unittest.main()
