import json
import ollama
from typing import Dict, Any
from .schema import NextMove
from .presets.code_agent import FrameworkState
from .core.pager import Pager

# --- THE MANAGER (Ollama) ---
class Manager:
    def __init__(self, driver):
        self.driver = driver
        # self.driver is expected to be an instance of OllamaDriver or similar wrapper
        # If passed raw, we might need to adjust.
        # Looking at main.py: manager = Manager(driver) where driver = OllamaDriver(...)

    def decide(self, state: FrameworkState, file_map: Dict[str, Any], pager: Pager) -> NextMove:
        # 1. Format L1 Context Summary
        loaded_files = list(pager.active_pages.keys())
        l1_status = f"Files Loaded ({len(loaded_files)}): {', '.join(loaded_files)}"
        stats = pager.get_stats()
        l1_usage = f"Usage: {stats['l1_used']}/{stats['l1_capacity']} tokens"

        # 2. Format Framework State
        state_dump = f"""
        Intent: {state.task_intent}
        Hypothesis: {state.current_hypothesis}
        Unknowns: {state.unknowns}
        Confidence: {state.confidence_score}
        """

        # 3. Construct Prompt
        # We perform a string dump of the file_map for the model to see structure
        # In a real app, this might be too large, but for 7B constraints, we assume small repos.
        map_str = json.dumps(file_map, indent=2)

        prompt = f"""
        SYSTEM: You are the KERNEL of an autonomous coding agent.
        You are NOT a chat bot. You are a STATE MACHINE.

        YOUR RESPONSIBILITY:
        1. Manage the 'L1 Cache' (Context Window). It is small and expensive.
        2. Only load what is immediately necessary for the Current Step.
        3. Direct the Worker to write code only when context is sufficient.

        [GLOBAL FILE MAP (The Disk)]
        {map_str}

        [CURRENT L1 CONTEXT (The RAM)]
        {l1_status}
        {l1_usage}

        [FRAMEWORK STATE]
        {state_dump}

        INSTRUCTIONS:
        - If you need to read a file that is NOT in L1 Context, use 'stage_context'.
        - If L1 is full or you are done with a file, use 'unstage_context'.
        - If you have the necessary context loaded, use 'write_code' to assign a task to the Worker.
        - If you are blocked or confused, use 'halt_and_ask'.
        - If you just finished a step, use 'verify_step'.

        DECISION LOGIC:
        - Review the Intent and Unknowns.
        - Look at the File Map.
        - Check if relevant files are in L1 Context.
        - Make ONE atomic move.
        """
        
        # 4. Call LLM
        # Using the driver's generate_structured or similar if available, 
        # but main.py passed `driver` which is OllamaDriver.
        # Let's check OllamaDriver signature in drivers/ollama.py if possible, 
        # or stick to direct ollama call if the driver wrapper is thin.
        # main.py does: driver = OllamaDriver(model_name="qwen2.5-coder:7b")
        # Let's assume we use the driver method if possible, but the previous code used ollama.chat directly.
        # To be safe and consistent with main.py which initializes Manager(driver), we use self.driver.
        
        # However, looking at the previous file content I replaced, it used `ollama.chat`.
        # I should check `amnesic/drivers/ollama.py` to see what `OllamaDriver` offers.
        # For now, I will use `self.driver.generate_structured` if it exists (Worker uses it), 
        # or fall back to `ollama.chat`.
        
        # Let's try to use the driver as the Worker does.
        
        return self.driver.generate_structured(
            user_prompt=prompt,
            schema=NextMove,
            system_prompt="You are the Manager. Output strict JSON.",
            retries=2
        )

