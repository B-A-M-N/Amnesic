from typing import Callable, Dict, Any, Optional
import logging

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.logger = logging.getLogger("amnesic.tools")

    def register_tool(self, name: str, func: Callable):
        """Registers a function as a tool the Manager can invoke."""
        self.tools[name] = func
        self.logger.info(f"Registered tool: {name}")

    def execute(self, name: str, **kwargs) -> Any:
        """Executes a registered tool by name."""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        
        self.logger.info(f"Executing tool: {name} with args {kwargs}")
        return self.tools[name](**kwargs)

    def get_tool_names(self) -> list[str]:
        return list(self.tools.keys())
