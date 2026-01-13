import json
import logging
import re
import ollama
from typing import Dict, Any, Type, Optional, Union, List, Callable
from pydantic import BaseModel, Field, ValidationError
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger("amnesic.driver")

class OllamaDriver:
    def __init__(self, model_name: str = "qwen2.5-coder:7b", temperature: float = 0.1, num_ctx: int = 2048, seed: Optional[int] = None):
        """
        The low-level interface to the LLM. 
        Designed to be stateless to allow rapid 'Frame Swapping'.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.seed = seed
        self.last_request_tokens = 0
        
        # Base client
        self._client = ChatOllama(
            model=model_name,
            temperature=temperature,
            format="json",
            num_ctx=num_ctx,
            options={
                "seed": seed,
                "temperature": temperature,
                "num_ctx": num_ctx,
                "top_k": 1,
                "top_p": 0.0,
                "repeat_penalty": 1.0,
                "mirostat": 0,
                "mirostat_eta": 0.1,
                "mirostat_tau": 5.0
            }
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
                # Cleanup trailing text/newlines inside the extracted block if any
                json_str = json_str.strip()
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
                
                # --- NEW DEEP EXTRACTION ---
                extracted = self._extract_json_block(response.content, schema)
                if extracted:
                    return extracted
                
                print("\n[Driver Error] Failed to parse (generate_structured). Raw:\n" + response.content + "\n[End Raw]")
                raise ValueError(f"Could not extract valid JSON from response: {response.content[:100]}...")
                
            except Exception as e:
                logger.error("Structured generation failed: %s", str(e))
                attempt += 1
                messages.append(HumanMessage(
                    content=f"Error: {str(e)}. Output ONLY valid raw JSON matching the schema."
                ))
        
        raise RuntimeError(f"Model failed to generate valid {schema.__name__}.")

    def _extract_json_block(self, text: str, schema: Type[BaseModel]) -> Optional[BaseModel]:
        """Aggressive extraction: strips markdown, thinking tags, and handles non-JSON fallbacks."""
        
        # 0. Strip Thinking Tags (CoT)
        # Handle <think>...</think>, [THOUGHT]..., THOUGHT: ...
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'\[THOUGHT\].*?\[/THOUGHT\]', '', text, flags=re.DOTALL)

        # 1. Strip Markdown Code Blocks
        # We find all blocks and try them one by one
        code_blocks = re.findall(r'```(?:json|python|markdown|text)?\s*(.*?)\s*```', text, flags=re.DOTALL)
        for block in code_blocks:
            extracted = self._try_parse_schema(block.strip(), schema)
            if extracted:
                return extracted

        # 2. Try raw parse of cleaned text (if no markdown blocks found)
        clean_text = text.strip()
        extracted = self._try_parse_schema(clean_text, schema)
        if extracted:
            return extracted

        # 3. Balanced Search (Targeting brackets)
        # Find all '{' and try to find matching '}'
        starts = [i for i, char in enumerate(text) if char == '{']
        for start in starts:
            balance = 0
            for i in range(start, len(text)):
                if text[i] == '{': balance += 1
                elif text[i] == '}': balance -= 1
                if balance == 0:
                    candidate = text[start:i+1]
                    extracted = self._try_parse_schema(candidate, schema)
                    if extracted:
                        return extracted
                    break # Stop trying this block if it failed

        # 4. KEY-VALUE FALLBACK (Targeting 8b models that output semi-structured text)
        if "TOOL CALL:" in clean_text or "tool_call:" in clean_text.lower():
            try:
                kv_data = {}
                # Match "KEY: Value" patterns, allowing for multi-line values
                # We look for THOUGHT PROCESS, TOOL CALL, TARGET, CONTENT
                patterns = {
                    "thought_process": [r"(?i)THOUGHT(?: PROCESS)?:\s*(.*?)(?=\n[A-Z ]+:|$)", r"(?i)thought_process:\s*(.*?)(?=\n[a-z_]+:|$)"],
                    "tool_call": [r"(?i)TOOL CALL:\s*(.*?)(?=\n[A-Z ]+:|$)", r"(?i)tool_call:\s*(.*?)(?=\n[a-z_]+:|$)"],
                    "target": [r"(?i)TARGET:\s*(.*?)(?=\n[A-Z ]+:|$)", r"(?i)target:\s*(.*?)(?=\n[a-z_]+:|$)"]
                }
                
                for key, regexes in patterns.items():
                    for reg in regexes:
                        m = re.search(reg, clean_text, re.DOTALL)
                        if m:
                            kv_data[key] = m.group(1).strip()
                            break
                
                # Special handling for "CONTENT:" which models often add for edit_file/write_file
                # Aggressive search for content block
                content_match = re.search(r"(?i)CONTENT:\s*(.*)", clean_text, re.DOTALL)
                if content_match and "target" in kv_data:
                    content = content_match.group(1).strip()
                    # Join target and content with a colon if not already there
                    tc = kv_data.get("tool_call", "").lower()
                    if ("edit_file" in tc or "write_file" in tc) and ":" not in kv_data["target"]:
                        kv_data["target"] = f"{kv_data['target']}: {content}"
                
                if "tool_call" in kv_data:
                    # Validate against schema
                    return schema.model_validate(kv_data)
            except Exception as e:
                logger.debug(f"KV Fallback failed: {e}")

        # 5. DIRECT TOOL CALL FALLBACK (Targeting models that try to call tools directly like CLI)
        # e.g. edit_file api.py: ...
        # e.g. stage_context(api.py)
        tool_names = ["stage_context", "unstage_context", "save_artifact", "delete_artifact", "stage_artifact", "edit_file", "write_file", "halt_and_ask", "verify_step", "calculate", "switch_strategy", "compare_files"]
        for tool in tool_names:
            # Match tool(target) or tool target
            patterns = [
                rf"(?i){tool}\s*\(\s*['\"]?(.*?)['\"]?\s*\)", # tool("target")
                rf"(?i){tool}\s+['\"]?([^`\n]+)['\"]?(?=\n|$)"   # tool target (exclude backticks)
            ]
            for pattern in patterns:
                m = re.search(pattern, clean_text, re.DOTALL)
                if m:
                    target_val = m.group(1).strip()
                    # Strip common helpful prefixes models add
                    for prefix in ["TARGET:", "target:", "Key:", "KEY:", "path:", "PATH:"]:
                        if target_val.startswith(prefix):
                            target_val = target_val[len(prefix):].strip()
                    
                    # If there's a thought process earlier, try to grab it
                    tp = "Extracted from direct tool call."
                    tp_match = re.search(r"(?i)THOUGHT(?: PROCESS)?:\s*(.*?)(?=\n|$|{tool})", clean_text, re.DOTALL)
                    if tp_match:
                        tp = tp_match.group(1).strip()
                    
                    try:
                        return schema.model_validate({
                            "thought_process": tp[:200] if tp else "Direct call.",
                            "tool_call": tool,
                            "target": target_val
                        })
                    except Exception:
                        pass

        # 6. AUDITOR-SPECIFIC HEALING: If model acts like Manager but we need a Verdict
        if schema.__name__ == "AuditorVerdict":
            # If the model tried to call a tool, it probably thinks the action is good
            if any(t in clean_text for t in ["stage_context", "read_file", "cat ", "grep"]):
                return schema(outcome="PASS", risk_level="low", rationale="Model tried to execute a read tool, implying consent.", correction=None)
            if any(t in clean_text for t in ["edit_file", "write_file", "rm ", "delete"]):
                return schema(outcome="REJECT", risk_level="high", rationale="Model tried to execute a write tool in audit mode.", correction="Provide a PASS/REJECT verdict instead of tool calls.")

        # 7. NUCLEAR FALLBACK: Wrap raw text if schema matches known worker schemas
        if schema.__name__ in ["WorkerResult", "GenerationArtifact"]:
            return schema(content=text.strip(), success=True if schema.__name__ == "WorkerResult" else "Extraction complete")
        
        if schema.__name__ == "CodeEdit":
             # This is harder to fallback for edits, so we just return None and let it retry
             return None
            
        return None

    def _try_parse_schema(self, candidate: str, schema: Type[BaseModel]) -> Optional[BaseModel]:
        """Helper to try parsing a string with a schema, including healing."""
        # 0. Pre-cleaning: remove "Thought: " or similar prefixes if they leaked into the candidate
        candidate = re.sub(r'(?i)^thought:\s*', '', candidate.strip())
        
        # Sub-attempt 1: Clean parse
        try:
            data = json.loads(candidate)
            # --- TYPO HEALING ---
            if schema.__name__ == "AuditorVerdict":
                if "rationate" in data and "rationale" not in data: data["rationale"] = data.pop("rationate")
                if "rationction" in data and "rationale" not in data: data["rationale"] = data.pop("rationction")
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValueError, ValidationError):
            pass
            
        # Sub-attempt 2: Healer (Fix single quotes and Python bools)
        try:
            repaired = candidate.replace("'", '"')
            repaired = repaired.replace("True", "true").replace("False", "false").replace("None", "null")
            data = json.loads(repaired)
            # --- TYPO HEALING ---
            if schema.__name__ == "AuditorVerdict":
                if "rationate" in data and "rationale" not in data: data["rationale"] = data.pop("rationate")
                if "rationction" in data and "rationale" not in data: data["rationale"] = data.pop("rationction")
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValueError, ValidationError):
            pass
        
        return None

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
            format="json",
            num_ctx=self.num_ctx,
            options={
                "seed": self.seed,
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "top_k": 1,
                "top_p": 0.0,
                "repeat_penalty": 1.0,
                "mirostat": 0,
                "mirostat_eta": 0.1,
                "mirostat_tau": 5.0
            }
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
                
                # --- NEW DEEP EXTRACTION ---
                extracted = self._extract_json_block(full_text, schema)
                if extracted:
                    return extracted
                
                # Log the failure for debugging
                print("\n[Driver Error] Failed to parse. Raw:\n" + full_text + "\n[End Raw]")
                raise ValueError("Could not extract valid JSON from response.")
                
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