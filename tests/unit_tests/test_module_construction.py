import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.environment import ExecutionEnvironment
from amnesic.core.tool_registry import ToolRegistry
from amnesic.tools.vector_store import VectorStore
from amnesic.tools.ast_mapper import StructuralMapper
from amnesic.tools.text_mapper import TextMapper
from amnesic.drivers.factory import get_driver
from amnesic.decision.manager import Manager
from amnesic.decision.auditor import Auditor
from amnesic.decision.worker import Worker

class TestModuleConstruction(unittest.TestCase):
    def test_manager_init(self):
        """Verify Manager initializes."""
        mock_driver = MagicMock()
        manager = Manager(driver=mock_driver)
        self.assertEqual(manager.driver, mock_driver)

    def test_auditor_init(self):
        """Verify Auditor initializes."""
        mock_driver = MagicMock()
        # Mock TextEmbedding to avoid model downloads during construction test
        with unittest.mock.patch('amnesic.decision.auditor.TextEmbedding') as mock_embedder:
            # Setup mock embedder instance
            mock_instance = mock_embedder.return_value
            mock_instance.embed.return_value = iter([[0.1, 0.2]])
            
            auditor = Auditor(goal="test", constraints=["NO_DELETES"], driver=mock_driver)
            self.assertEqual(auditor.driver, mock_driver)
            self.assertEqual(auditor.constraints, ["NO_DELETES"])

    def test_worker_init(self):
        """Verify Worker initializes."""
        mock_driver = MagicMock()
        worker = Worker(driver=mock_driver)
        self.assertEqual(worker.driver, mock_driver)

    def test_execution_environment_init(self):
        """Verify ExecutionEnvironment initializes correctly."""
        env = ExecutionEnvironment(root_dir=".")
        self.assertEqual(env.root_dir, ".")
        self.assertIsInstance(env.mapper, StructuralMapper)

    def test_tool_registry_init(self):
        """Verify ToolRegistry initializes empty."""
        registry = ToolRegistry()
        self.assertEqual(len(registry.tools), 0)
        self.assertEqual(registry.get_tool_names(), [])

    def test_vector_store_init(self):
        """Verify VectorStore initializes with collections."""
        mock_driver = MagicMock()
        store = VectorStore(driver=mock_driver)
        self.assertEqual(store.driver, mock_driver)
        self.assertIn("code", store.collections)
        self.assertIn("text", store.collections)

    def test_structural_mapper_init(self):
        """Verify StructuralMapper default ignores."""
        mapper = StructuralMapper(root_dir=".")
        self.assertEqual(mapper.root_dir, ".")
        self.assertIn(".git", mapper.ignore_dirs)
        self.assertIn("__pycache__", mapper.ignore_dirs)

    def test_text_mapper_init(self):
        """Verify TextMapper default extensions."""
        mapper = TextMapper(root_dir=".")
        self.assertEqual(mapper.root_dir, ".")
        self.assertIn(".md", mapper.extensions)
        self.assertIn(".txt", mapper.extensions)

    def test_driver_factory_ollama(self):
        """Verify Driver Factory returns Ollama driver."""
        # Ollama doesn't require API key
        driver = get_driver(provider="ollama", model="qwen2.5-coder:7b")
        from amnesic.drivers.ollama import OllamaDriver
        self.assertIsInstance(driver, OllamaDriver)

    def test_driver_factory_openai(self):
        """Verify Driver Factory returns OpenAI driver."""
        # Mock the entire openai module before it's imported in amnesic.drivers.llm
        with unittest.mock.patch.dict(sys.modules, {'openai': MagicMock()}):
            driver = get_driver(provider="openai", model="gpt-4o", api_key="sk-test")
            from amnesic.drivers.llm import OpenAIDriver
            self.assertIsInstance(driver, OpenAIDriver)

    def test_driver_factory_invalid(self):
        """Verify Driver Factory raises error on unknown provider."""
        with self.assertRaises(ValueError):
            get_driver(provider="unknown", model="model")

if __name__ == "__main__":
    unittest.main()
