import os
from typing import List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field
from amnesic.drivers.factory import get_driver

class ControlMove(BaseModel):
    thought: str = Field(default="No thought provided", description="Reasoning")
    tool: Literal["read_file", "answer", "write_file", "stage_context"] = Field(..., alias="action")
    arg: Union[str, dict] = Field(..., alias="path")

    model_config = {
        "populate_by_name": True,
        "extra": "allow"
    }

class StandardReActAgent:
    def __init__(self, mission: str, model: str = "rnj-1:8b-cloud", token_limit: int = 32768):
        self.mission = mission
        self.driver = get_driver("ollama", model)
        self.token_limit = token_limit
        self.history = [] 
        self.turns = 0
        self.last_file_read = "EMPTY"

    def step(self):
        self.turns += 1
        system_prompt = (
            f"MISSION: {self.mission}\n"
            "You are a standard ReAct agent with a single context window.\n"
            "TOOLS AVAILABLE: read_file(path), answer(result), write_file(path: content).\n"
            "OUTPUT FORMAT: You MUST output ONLY raw JSON. No thought process outside JSON. No markdown code blocks.\n"
            "SCHEMA: {'thought': '...', 'tool': '...', 'arg': '...'}\n"
        )
        
        context_tokens = len(system_prompt) // 4
        active_history = []
        current_history_tokens = 0
        hit_limit = False
        
        for msg in reversed(self.history):
            msg_str = f"{msg['role']}: {msg['content']}\n"
            msg_tokens = len(msg_str) // 4
            if context_tokens + current_history_tokens + msg_tokens < self.token_limit:
                active_history.insert(0, msg_str)
                current_history_tokens += msg_tokens
            else: 
                hit_limit = True
                break
                
        full_prompt = system_prompt + "\n\n[HISTORY]\n" + "".join(active_history) + "\n\nAction:"
        total_tokens = context_tokens + current_history_tokens

        try:
             move = self.driver.generate_structured(
                 user_prompt=full_prompt,
                 schema=ControlMove,
                 system_prompt="Output ONLY raw JSON."
             )
        except Exception as e:
            return {
                "turn": self.turns,
                "action": "error", "arg": str(e), "thought": "Crash", 
                "context_len": total_tokens, "limit": self.token_limit,
                "file": "ERROR", "window_status": "CRASH"
            }

        observation = "Action processed."
        arg_str = str(move.arg)
        
        if move.tool == "read_file" or move.tool == "stage_context":
            path = move.arg if isinstance(move.arg, str) else move.arg.get("path", str(move.arg))
            arg_str = path
            if os.path.exists(path):
                with open(path, 'r') as f: observation = f.read()
            else: observation = "Error: File not found."
            self.last_file_read = path
            
        self.history.append({"role": "assistant", "content": f"Call: {move.tool}({arg_str})"})
        self.history.append({"role": "user", "content": f"Observation: {observation}"})
        
        return {
            "turn": self.turns,
            "action": move.tool, 
            "arg": arg_str, 
            "thought": move.thought,
            "context_len": total_tokens, 
            "limit": self.token_limit,
            "file": self.last_file_read,
            "window_status": "MAX" if hit_limit else "OK"
        }
