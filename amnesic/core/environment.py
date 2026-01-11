import os
from typing import Dict, Any, Optional
from amnesic.tools.ast_mapper import StructuralMapper

class ExecutionEnvironment:
    """
    The Hardware Abstraction Layer (HAL) for the Amnesic Agent.
    Provides 'Ground Truth' about the physical environment (files, AST, sizes)
    to prevent the Manager from hallucinating file existence or content.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.mapper = StructuralMapper(root_dir=root_dir)
        
    def refresh_substrate(self):
        """
        Maps ANY environment on the fly.
        Discovers file structures, AST nodes, and data relations.
        Returns the raw FileMap list.
        """
        # Scans the repository to create a global file map
        # This is the "Menu" the Manager sees.
        return self.mapper.scan_repository() 

    def get_context_bounds(self, target_path: str) -> Optional[Dict[str, Any]]:
        """
        Returns 'Physical' constraints of a file (size, type).
        Used by the Auditor to enforce memory limits before loading.
        """
        # Handle relative paths safely
        full_path = os.path.abspath(os.path.join(self.root_dir, target_path))
        
        # Security check: Ensure we don't traverse outside root
        if not full_path.startswith(os.path.abspath(self.root_dir)):
            return None

        if os.path.exists(full_path):
            return {
                "size_bytes": os.path.getsize(full_path),
                "is_executable": target_path.endswith(".py"),
                "is_readable": os.access(full_path, os.R_OK)
            }
        return None
