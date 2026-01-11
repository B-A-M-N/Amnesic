import json
import logging
import re
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
        # 0. Pre-cleaning: Remove Markdown Code Blocks
        # Pattern finds ```json ... ``` or just ``` ... ``` and extracts content
        code_block_pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(code_block_pattern, content, re.DOTALL)
        if match:
            content = match.group(1)

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

        # 3. Regex Fallback (The "Hammer")
        try:
            match = re.search(r'(\{.*\})', content, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                return schema.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            pass

        # 4. JSON Repair (The "Healer") - fix common small model errors
        try:
            # Try to fix single quotes to double quotes (naive but effective for simple dicts)
            # This regex looks for 'key': or 'value' patterns
            repaired = content.replace("'", '"')
            repaired = repaired.replace("True", "true").replace("False", "false").replace("None", "null")
            # Try finding braces again in repaired string
            start = repaired.find('{')
            end = repaired.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = repaired[start:end]
                data = json.loads(json_str)
                return schema.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            pass
            
        raise ValueError(f"Could not extract valid JSON from response. Content preview: {content[:100]}...")

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
                
                full_text = full_content
                
                # --- PATCH START ---
                # Attempt 1: Standard Parse (Fastest)
                try:
                    return self._safe_parse_json(full_text, schema)
                except Exception:
                    pass

                # Attempt 2: Candidate Iteration (Robust)
                # Iterate through every '{' in the text and try to parse a valid object
                decoder = json.JSONDecoder()
                pos = 0
                parsed_candidates = []
                
                while True:
                    pos = full_text.find('{', pos)
                    if pos == -1:
                        break
                    try:
                        # raw_decode returns (obj, end_index)
                        obj, end = decoder.raw_decode(full_text, pos)
                        # Try to validate schema immediately
                        try:
                            return schema.model_validate(obj)
                        except Exception:
                            # Valid JSON but wrong schema? Save for inspection if needed, or ignore
                            pass
                        # Move past this object
                        pos = end
                    except json.JSONDecodeError:
                        # Not a valid object start, move forward one char
                        pos += 1
                
                # If we get here, no valid schema object was found
                print(f"\n[Driver Error] Failed to parse. Raw: {full_text[:200]}...")
                raise ValueError("Could not extract valid JSON from response.")
                # --- PATCH END ---
                
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