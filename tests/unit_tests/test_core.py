import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession
from amnesic.auditor import Auditor

class TestAmnesicCore(unittest.TestCase):
    def test_imports(self):
        """Ensure core components are exposed correctly."""
        self.assertTrue(AmnesicSession)
        self.assertTrue(Auditor)

    def test_auditor_init(self):
        """Ensure Auditor initializes."""
        auditor = Auditor()
        self.assertTrue(auditor)

if __name__ == "__main__":
    unittest.main()
