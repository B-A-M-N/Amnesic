import json
import logging
import ollama
from typing import Dict, Any, Type, Optional, Union, List, Callable
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger("amnesic.driver")

class OllamaDriver:
    def __init__(self, model_name: str = "qwen2.5-coder:7b", temperature: float = 0.1, num_ctx: int = 2048):
        """
        The low-level interface to the LLM. 
        Designed to be stateless to allow rapid 'Frame Swapping'.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.last_request_tokens = 0
        
        # Base client
        self._client = ChatOllama(
            model=model_name,
            temperature=temperature,
            format="json",
            num_ctx=num_ctx,
            keep_alive="5m"
        )

    def embed(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the given text.
        """
        try:
            # Using the official python ollama client for embeddings
            response = ollama.embeddings(model=self.model_name, prompt=text)
            return response["embedding"]
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

    def clear_internal_chat_history(self):
        """
        Explicitly clears any internal state/history in the driver.
        For this stateless implementation, it's a no-op but serves as a logic gate.
        """
        pass

    def _update_token_usage(self, system_prompt: str, user_prompt: str):
        # Rough approximation: 4 chars per token
        total_chars = len(system_prompt) + len(user_prompt)
        self.last_request_tokens = total_chars // 4

    def _safe_parse_json(self, content: str, schema: Type[BaseModel]) -> BaseModel:
        """
        Attempts to parse JSON from content, with healing for Markdown code blocks
        and extra text.
        """
        import json
        
        # 1. Try Clean Parse
        try:
            data = json.loads(content)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            pass

        # 2. Extract JSON using strict boundaries (find first { and last })
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = content[start:end]
                data = json.loads(json_str)
                return schema.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            pass
            
        raise ValueError("Could not extract valid JSON from response.")

    def generate_structured(
        self, 
        user_prompt: str, 
        schema: Type[BaseModel], 
        system_prompt: str,
        retries: int = 2
    ) -> BaseModel:
        """
        Executes a reasoning step within a specific Amnesic Frame.
        """
        self._update_token_usage(system_prompt, user_prompt)
        
        # We use raw generation + parsing to have full control over the healing
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        attempt = 0
        while attempt <= retries:
            try:
                if attempt > 0:
                    logger.warning(f"Retry attempt {attempt}...")
                
                # Use standard invoke to get raw text, then parse ourselves
                # This bypasses LangChain's strict parser which might fail before we can heal
                response = self._client.invoke(messages)
                return self._safe_parse_json(response.content, schema)
                
            except Exception as e:
                logger.error(f"Structured generation failed: {str(e)}")
                attempt += 1
                messages.append(HumanMessage(
                    content=f"Error: {str(e)}. Output ONLY valid raw JSON matching the schema."
                ))
        
        raise RuntimeError(f"Model failed to generate valid {schema.__name__}.")

    def generate_structured_with_stream(
        self, 
        user_prompt: str, 
        schema: Type[BaseModel], 
        system_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        retries: int = 2
    ) -> BaseModel:
        """
        Streams the raw JSON output to a callback while accumulating for parsing.
        This allows the user to see the reasoning (rationale) as it is generated.
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # We use a raw client for streaming because with_structured_output hides chunks
        raw_client = ChatOllama(
            model=self.model_name,
            temperature=self.temperature,
            format="json",
            num_ctx=self.num_ctx,
            keep_alive="5m"
        )

        attempt = 0
        while attempt <= retries:
            full_content = ""
            try:
                for chunk in raw_client.stream(messages):
                    content = chunk.content
                    full_content += content
                    if stream_callback:
                        stream_callback(content)
                
                # Parse the final accumulated string using safe parser
                return self._safe_parse_json(full_content, schema)
                
            except Exception as e:
                logger.error(f"Streaming structured generation failed: {str(e)}")
                attempt += 1
                messages.append(HumanMessage(
                    content="Error: Invalid JSON. Output ONLY raw JSON."
                ))
        
        raise RuntimeError(f"Model failed to generate valid {schema.__name__} after {retries} retries.")

    def generate_raw(self, prompt: str, system_prompt: str) -> str:
        self._update_token_usage(system_prompt, prompt)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]
        response = self._client.invoke(messages)
        return response.content