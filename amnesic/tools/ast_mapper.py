import ast
import os
from typing import List, Dict, TypedDict

# --- Schema for the "Map" ---
class FunctionNode(TypedDict):
    name: str
    args: List[str]
    line_start: int
    line_end: int
    docstring: str  # Critical for Reranker relevance checks

class ClassNode(TypedDict):
    name: str
    methods: List[FunctionNode]
    line_start: int
    line_end: int

class FileMap(TypedDict):
    path: str
    classes: List[ClassNode]
    functions: List[FunctionNode]
    imports: List[str] # Helpful for dependency tracking

class StructuralMapper:
    def __init__(self, root_dir: str, ignore_dirs: List[str] = None, include_root: bool = False):
        self.root_dir = root_dir
        self.include_root = include_root
        self.ignore_dirs = ignore_dirs or [".git", "__pycache__", "venv", "node_modules", ".gemini", ".amnesic_cache"]

    def scan_repository(self) -> List[FileMap]:
        """
        Walks the directory and builds the Structural Map.
        This is the 'Menu' given to the Manager.
        """
        repository_map = []

        for root, dirs, files in os.walk(self.root_dir):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                full_path = os.path.join(root, file)
                # Only include root name if explicitly requested (e.g. Multi-Repo)
                if self.include_root:
                    base_name = os.path.basename(self.root_dir)
                    rel_path = os.path.join(base_name, os.path.relpath(full_path, self.root_dir))
                else:
                    rel_path = os.path.relpath(full_path, self.root_dir)
                
                if file.endswith(".py"):
                    try:
                        file_map = self._parse_file(full_path, rel_path)
                        repository_map.append(file_map)
                    except Exception as e:
                        print(f"[WARN] Could not parse {rel_path}: {e}")
                else:
                    # Generic handling for non-python files
                    # We just list them so the Manager knows they exist
                    repository_map.append({
                        "path": rel_path,
                        "classes": [],
                        "functions": [],
                        "imports": []
                    })

        return repository_map

    def to_indexable_nodes(self, repository_map: List[FileMap]) -> List[Dict]:
        """
        Converts a Repository Map into a list of chunks for Vector Indexing.
        Each chunk contains the signature and docstring.
        """
        nodes = []
        for file in repository_map:
            path = file["path"]
            
            # Index standalone functions
            for func in file["functions"]:
                nodes.append({
                    "id": f"{path}::{func['name']}",
                    "content": f"Function: {func['name']}({', '.join(func['args'])})\nDoc: {func['docstring']}",
                    "metadata": {"path": path, "type": "function", "name": func["name"]}
                })
                
            # Index classes and their methods
            for cls in file["classes"]:
                nodes.append({
                    "id": f"{path}::{cls['name']}",
                    "content": f"Class: {cls['name']}\nMethods: {', '.join([m['name'] for m in cls['methods']])}",
                    "metadata": {"path": path, "type": "class", "name": cls["name"]}
                })
                for method in cls["methods"]:
                    nodes.append({
                        "id": f"{path}::{cls['name']}.{method['name']}",
                        "content": f"Method: {cls['name']}.{method['name']}({', '.join(method['args'])})\nDoc: {method['docstring']}",
                        "metadata": {"path": path, "type": "method", "name": method["name"], "class": cls["name"]}
                    })
        return nodes

    def _parse_file(self, full_path: str, rel_path: str) -> FileMap:
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()
            tree = ast.parse(source)

        classes = []
        functions = []
        imports = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
            elif isinstance(node, ast.ClassDef):
                classes.append(self._parse_class(node))
            elif isinstance(node, ast.FunctionDef):
                functions.append(self._parse_function(node))

        return {
            "path": rel_path,
            "classes": classes,
            "functions": functions,
            "imports": imports
        }

    def _parse_function(self, node: ast.FunctionDef) -> FunctionNode:
        return {
            "name": node.name,
            "args": [arg.arg for arg in node.args.args],
            "line_start": node.lineno,
            "line_end": node.end_lineno,
            # Extract first line of docstring only (Save tokens)
            "docstring": (ast.get_docstring(node) or "").split('\n')[0]
        }

    def _parse_class(self, node: ast.ClassDef) -> ClassNode:
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(self._parse_function(item))
        
        return {
            "name": node.name,
            "methods": methods,
            "line_start": node.lineno,
            "line_end": node.end_lineno
        }