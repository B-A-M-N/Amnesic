import os
import sys
import json
import logging
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field, ValidationError
from amnesic.drivers.factory import get_driver

# Suppress library logging to avoid output spam
logging.getLogger("amnesic.driver").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)

# Shared Schema for Control Agents
# ALIGNED with standard ReAct patterns (Action/Action Input) to help smaller models
class ControlMove(BaseModel):
    thought: str = Field(..., description="Reasoning")
    action: Literal["read_file", "write_file", "answer", "scan_file"] = Field(..., description="The tool to use")
    action_input: str = Field(..., description="The argument for the tool")

class StandardReActAgent:
    """
    A Standard ReAct Agent (Control Group).
    - No Amnesic Architecture (No Pager, No Auditor).
    - Uses a simple Sliding Window for context.
    - Persists history indefinitely until tokens run out.
    """
    def __init__(self, mission: str, model: str = "rnj-1:8b-cloud", token_limit: int = 32768):
        self.mission = mission
        self.driver = get_driver("ollama", model)
        self.token_limit = token_limit
        self.history = [] 
        self.turns = 0
        self.last_file_read = "EMPTY"
        self.artifacts = {} # To track outputs

    def step(self):
        self.turns += 1
        
        # Explicit Schema Injection in Prompt for Robustness
        schema_desc = (
            "RESPONSE FORMAT (JSON ONLY):\n"
            "{\n"
            '  "thought": "Your reasoning here...",\n'
            '  "action": "read_file" | "write_file" | "answer",\n'
            '  "action_input": "filename" | "filename|content"\n'
            "}\n"
        )
        
        system_prompt = (
            f"MISSION: {self.mission}\n"
            "You are a standard ReAct agent with a single context window.\n"
            "TOOLS AVAILABLE:\n"
            "- read_file(path): Reads a file.\n"
            "- write_file(path, content): Writes a file. ARGUMENT FORMAT: 'path|content'\n"
            "- answer(result): Ends the mission.\n"
            f"{schema_desc}\n"
            "Output JSON."
        )
        
        # Sliding Window Enforcement
        context_tokens = len(system_prompt) // 4
        active_history = []
        
        current_history_tokens = 0
        hit_limit = False
        
        # Simple sliding window: Take newest messages first until limit
        for msg in reversed(self.history):
            msg_str = f"{msg['role']}: {msg['content']}\n"
            msg_tokens = len(msg_str) // 4
            if context_tokens + current_history_tokens + msg_tokens < self.token_limit:
                active_history.insert(0, msg_str)
                current_history_tokens += msg_tokens
            else: 
                hit_limit = True
                break
                
        full_prompt = system_prompt + "\n\n[HISTORY]\n" + "".join(active_history) + "\n\nAction (JSON):"
        total_tokens = context_tokens + current_history_tokens

        try:
             move = self.driver.generate_structured(
                 user_prompt=full_prompt,
                 schema=ControlMove,
                 system_prompt="Output ONLY raw JSON matching the schema."
             )
        except Exception as e:
            # Catch validation errors gracefully
            return {
                "turn": self.turns,
                "action": "error", "arg": f"Format Error: {str(e)[:50]}...", "thought": "Failed to parse output.", 
                "context_len": total_tokens, "limit": self.token_limit,
                "file": self.last_file_read,
                "window_status": "CRASH",
                "full_context_snapshot": "".join(active_history)
            }

        observation = ""
        if move.action == "read_file":
            self.last_file_read = move.action_input
            if os.path.exists(move.action_input):
                with open(move.action_input, 'r') as f: observation = f"FILE_CONTENT({move.action_input}):\n{f.read()}"
            else: observation = f"ERROR: File {move.action_input} not found."
            
        elif move.action == "write_file":
            if "|" in move.action_input:
                path, content = move.action_input.split("|", 1)
                with open(path.strip(), 'w') as f: f.write(content)
                observation = f"File {path} written."
                self.artifacts[path.strip()] = content
            else:
                observation = "ERROR: write_file requires 'path|content'."

        elif move.action == "answer": 
            observation = "Mission Complete."
            
        self.history.append({"role": "assistant", "content": f"Call: {move.action}({move.action_input})"})
        self.history.append({"role": "user", "content": f"Observation: {observation}"})
        
        display_action = move.action
        
        status_str = "OK"
        if hit_limit:
            status_str = "MAX (Frag)" if total_tokens < self.token_limit * 0.9 else "MAX"

        return {
            "turn": self.turns,
            "action": display_action, 
            "arg": move.action_input, 
            "thought": move.thought,
            "context_len": total_tokens, 
            "limit": self.token_limit,
            "file": self.last_file_read if move.action == "read_file" else "EMPTY",
            "window_status": status_str,
            "full_context_snapshot": "".join(active_history) 
        }
