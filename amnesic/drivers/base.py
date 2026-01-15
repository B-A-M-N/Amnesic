from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, Callable
from pydantic import BaseModel

class LLMDriver(ABC):
    """
    Abstract Base Class for LLM interactions.
    Ensures that any model plugged into Amnesic follows the same contract.
    """
    last_request_tokens: int = 0

    def _update_token_usage(self, system_prompt: str, user_prompt: str) -> None:
        """
        Updates the token usage counter for the last request.
        Uses a rough approximation of 4 characters per token.
        """
        total_chars = len(system_prompt) + len(user_prompt)
        self.last_request_tokens = total_chars // 4

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generates a vector embedding for the given text."""
        pass

    @abstractmethod
    def generate_structured(
        self, 
        user_prompt: str, 
        schema: Type[BaseModel], 
        system_prompt: str,
        retries: int = 2
    ) -> BaseModel:
        """Executes a reasoning step and returns a structured Pydantic model."""
        pass

    @abstractmethod
    def generate_structured_with_stream(
        self, 
        user_prompt: str, 
        schema: Type[BaseModel], 
        system_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        retries: int = 2
    ) -> BaseModel:
        """Streams raw output to a callback while parsing the final result into a Pydantic model."""
        pass

    @abstractmethod
    def generate_raw(self, prompt: str, system_prompt: str) -> str:
        """Returns a simple string response from the LLM."""
        pass

