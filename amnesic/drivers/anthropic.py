import json
import logging
from typing import List, Type, Optional, Callable
from pydantic import BaseModel
from .base import LLMDriver

logger = logging.getLogger("amnesic.driver.anthropic")

class AnthropicDriver(LLMDriver):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20240620", seed: Optional[int] = None):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Anthropic driver requires 'anthropic' package. Please install it.")
        
        self.model_name = model_name
        self.seed = seed
        self.client = anthropic.Anthropic(api_key=api_key)

    def embed(self, text: str) -> List[float]:
        # Anthropic doesn't have a public embedding API that is standard yet in the SDK 
        # (mostly people use Voyage or OpenAI for embeddings with Claude).
        # We'll return empty or raise, or maybe use a placeholder.
        logger.warning("Anthropic native embeddings not supported directly. Returning empty vector.")
        return []

    def generate_structured(self, user_prompt: str, schema: Type[BaseModel], system_prompt: str, retries: int = 2) -> BaseModel:
        # Anthropic supports tool use or JSON mode. We can use tool use for structured output.
        # Or just prompt engineering with JSON mode.
        return self.generate_structured_with_stream(user_prompt, schema, system_prompt, None, retries)

    def generate_structured_with_stream(
        self, 
        user_prompt: str, 
        schema: Type[BaseModel], 
        system_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        retries: int = 2
    ) -> BaseModel:
        
        # Construct the tool/function definition from the schema
        # This is a simplified mapping. Complex schemas might need recursive parsing.
        tool_definition = {
            "name": "submit_result",
            "description": f"Submit the final structured result conforming to {schema.__name__}",
            "input_schema": schema.model_json_schema()
        }

        messages = [
            {"role": "user", "content": user_prompt}
        ]

        attempt = 0
        while attempt <= retries:
            try:
                # We'll use the Messages API with tools
                # Note: Streaming with tools in Anthropic SDK is a bit complex for a simple hook.
                # For now, we'll implement non-streaming for the final tool call, 
                # but maybe stream the text leading up to it if we were doing Chain of Thought.
                # Here we just want the result.
                
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=[tool_definition],
                    tool_choice={"type": "tool", "name": "submit_result"}
                )

                # Anthropic usually returns a tool_use block
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        return schema.model_validate(content_block.input)
                
                # If no tool called
                raise ValueError("No tool call found in Anthropic response")

            except Exception as e:
                logger.error(f"Anthropic generation failed: {e}")
                attempt += 1
                
        raise RuntimeError(f"Anthropic failed to generate valid {schema.__name__}")

    def generate_raw(self, prompt: str, system_prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
