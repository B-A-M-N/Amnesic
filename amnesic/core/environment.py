import os
from typing import Dict, Any, Optional, List
from amnesic.tools.ast_mapper import StructuralMapper

class ExecutionEnvironment:
    """
    The Hardware Abstraction Layer (HAL) for the Amnesic Agent.
    Supports Multi-Root Workspaces.
    """
    def __init__(self, root_dirs: List[str]):
        self.root_dirs = [os.path.abspath(rd) for rd in root_dirs]
        # Mapper only includes root name if we have multiple roots to disambiguate
        use_prefix = len(self.root_dirs) > 1
        self.mappers = [StructuralMapper(root_dir=rd, include_root=use_prefix) for rd in self.root_dirs]
        
    def refresh_substrate(self):
        """
        Aggregates file maps from all registered roots.
        """
        global_map = []
        for mapper in self.mappers:
            global_map.extend(mapper.scan_repository())
        return global_map

    def get_context_bounds(self, target_path: str) -> Optional[Dict[str, Any]]:
        """
        Returns 'Physical' constraints of a file.
        Checks across all roots.
        """
        target_abs = os.path.abspath(target_path)
        
        # Check if it belongs to any root
        belongs_to_root = any(target_abs.startswith(rd) for rd in self.root_dirs)
        if not belongs_to_root:
            return None

        if os.path.exists(target_abs):
            return {
                "size_bytes": os.path.getsize(target_abs),
                "is_executable": target_path.endswith(".py"),
                "is_readable": os.access(target_abs, os.R_OK)
            }
        return None
