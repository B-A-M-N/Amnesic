from typing import Dict, Any, Optional, Callable, List
from ..drivers.ollama import OllamaDriver
from ..presets.code_agent import MANAGER_SYSTEM_PROMPT, ManagerMove, FrameworkState
from ..core.pager import Pager
from ..core.memory import compress_history

class Manager:
    def __init__(self, driver: OllamaDriver, elastic_mode: bool = False):
        self.driver = driver
        self.elastic_mode = elastic_mode

    def decide(self, state: FrameworkState, file_map: list, pager: Optional[Pager] = None, active_context: str = "", l2_list: list = [], stream_callback: Optional[Callable] = None, history_block: str = "") -> ManagerMove:
        """
        The Brain: Deliberates on the next step.
        """
        # Define Elastic vs Strict Rules
        if self.elastic_mode:
            amnesia_rule = "You are in ELASTIC MODE. You can hold multiple files in L1 RAM for cross-referencing."
            eviction_rule = "Files remain in L1 until you explicitly 'unstage_context' them or memory hits capacity."
            l1_rule_prompt = "2. L1 RAM RULE: You can hold MULTIPLE files in L1. Load what you need to see together."
        else:
            amnesia_rule = "If a file is in the CURRENT L1 CACHE, you MUST use 'save_artifact', 'edit_file' or 'verify_step'."
            eviction_rule = "Once an artifact is saved, the kernel will AUTO-EVICT the file to clear space."
            l1_rule_prompt = "2. L1 RAM RULE: Only ONE file can be in L1 at a time. If [L1 RAM STATUS] shows a file and you need another, you MUST use 'unstage_context' first."

        # 1. Update MMU Clock
        if pager:
            pager.tick()
            l1_view = pager.render_context()
            l2_view = list(pager.swap_disk.keys())
        else:
            l1_view = active_context
            l2_view = l2_list
        
        # Prepare State Dump
        state_dump = state.model_dump_json(indent=2)
        
        # Prepare Context (L1 Cache)
        # Format the file map into a clean, readable list for the 3B model
        map_lines = []
        for f in file_map:
            path = f.get('path', 'unknown')
            # Handle both raw AST list and simplified dict
            if isinstance(f, dict) and 'classes' in f:
                classes = [c['name'] for c in f.get('classes', [])]
                funcs = [func['name'] for func in f.get('functions', [])]
            elif isinstance(f, dict) and 'classes_and_funcs' in f: # hypothetical
                classes = []
                funcs = []
            else:
                 # Fallback for simple dicts or strings
                 classes = []
                 funcs = []

            line = f"- {path}"
            if classes:
                line += f" [Classes: {', '.join(classes)}]"
            if funcs:
                line += f" [Funcs: {', '.join(funcs)}]"
            map_lines.append(line)
            
        map_summary = "\n".join(map_lines)[:2500]
        
        # Tools are dynamically fetched from the schema to ensure sync
        tools_list = ManagerMove.model_json_schema()['properties']['tool_call']['enum']
        
        l1_files = [f.replace("FILE:", "") for f in (list(pager.active_pages.keys()) if pager else [active_context] if active_context else [])]
        l2_files = [f.replace("FILE:", "") for f in (l2_list if not pager else list(pager.swap_disk.keys()))]
        
        # Render ACTUAL content for the prompt
        active_content = pager.render_context() if pager else active_context

        # Format artifacts for prompt
        found_artifacts = [f"{a.identifier}: {a.summary}" for a in state.artifacts]
        artifacts_summary = ", ".join(found_artifacts) if found_artifacts else "None"
        
        # Prepare critical feedback block
        feedback_str = ""
        if state.last_action_feedback:
            feedback_str = f"\n[SYSTEM FEEDBACK]: {state.last_action_feedback}"
            
        # DETERMINISTIC OVERRIDE: Check for Mission Completion
        # This allows the kernel to bypass the LLM for the final step in validated proofs.
        artifact_ids = [a.identifier for a in state.artifacts]
        if "TOTAL" in artifact_ids:
            total_val = next(a.summary for a in state.artifacts if a.identifier == "TOTAL")
            return ManagerMove(
                thought_process="The TOTAL artifact is present. The mission is complete. Reporting final sum.",
                tool_call="halt_and_ask",
                target=total_val
            )

        # Strategy Injection (Decouples specific test logic from core)
        strategy_block = state.strategy if state.strategy else "1. Focus on the Mission objectives."

        prompt = f"""
        [ENVIRONMENT STRUCTURE]
        {map_summary}

        {history_block}
        
        [L1 RAM STATUS]
        {active_context}

        [CURRENT L1 CONTEXT CONTENT]
        {pager.render_context() if pager else "NO CONTENT RENDERED"} 

        [SHARED GROUND TRUTH (ARTIFACTS)]
        {artifacts_summary}

        [INSTRUCTIONS (Cognitive Load Shaping)]
        {strategy_block}
        {l1_rule_prompt}
        3. Identify what is MISSING from the Shared Ground Truth.
        4. If you have all necessary inputs, use 'verify_step' or 'calculate'.
        5. If verification fails (values do not match), do NOT retry. Immediately 'halt_and_ask' to report the discrepancy.
        6. If the Mission is complete, use 'halt_and_ask'.

        {feedback_str}
        
        Decide the next move based on the infrastructure truth and context content.
        """
        
        formatted_system = MANAGER_SYSTEM_PROMPT.format(
            state_dump=state_dump, 
            tools_available=", ".join(tools_list),
            l1_files=l1_files,
            l2_files=l2_files,
            artifacts=artifacts_summary,
            feedback=feedback_str,
            amnesia_rule=amnesia_rule,
            eviction_rule=eviction_rule
        )
        
        try:
            decision_model = self.driver.generate_structured_with_stream(
                user_prompt=prompt, 
                schema=ManagerMove,
                system_prompt=formatted_system,
                stream_callback=stream_callback
            )
            return decision_model
            
        except Exception as e:
            print(f"!! Kernel Panic: {str(e)}")
            return ManagerMove(
                thought_process=f"Kernel panic: {str(e)}",
                tool_call="halt_and_ask",
                target="error"
            )

# --- LangGraph Adapter ---
_shared_driver = OllamaDriver()
_shared_manager = Manager(_shared_driver)

def node_manager(state: dict):
    """
    Wraps the Manager for LangGraph execution.
    """
    fw_state = state['framework_state']
    # Re-instantiate manager to ensure elastic_mode is synchronized with state
    # (Note: session.py already sets this on its manager_node, 
    # but the LangGraph node_manager might be called independently)
    elastic_mode = getattr(fw_state, 'elastic_mode', False)
    manager = Manager(_shared_driver, elastic_mode=elastic_mode)

    # Adapter for file map: session.py uses a dict, Manager wants a list
    raw_map = state.get('active_file_map', {})
    
    # Reconstruct list format for Manager
    # session.py: {path: [list of names]}
    file_list = []
    if isinstance(raw_map, dict):
        for path, items in raw_map.items():
            # separating classes and funcs is hard without metadata, 
            # so we just put everything in 'classes' for display purposes or handle it generically
            file_list.append({
                'path': path, 
                'classes': [{'name': i} for i in items], 
                'functions': []
            })
    else:
        file_list = raw_map if isinstance(raw_map, list) else []

    # Construct history block
    history = state.get('decision_history', [])
    history_lines = []
    for i, h in enumerate(history):
         # h is DecisionTrace dict
         history_lines.append(f"Turn {i}: {h['tool_call']} -> {h['auditor_verdict']}")
    
    # Apply compression
    compressed_history = compress_history(history_lines, max_turns=5)
    history_block = "[HISTORY]\n" + compressed_history if compressed_history else ""

    decision = _shared_manager.decide(
        state=fw_state, 
        file_map=file_list, 
        active_context=state.get('current_context_window', ""),
        l2_list=[], # L2 not fully supported in stateless mode yet
        pager=state.get('pager'), # Pass pager if available
        history_block=history_block
    )
    
    # Return MUST match AgentState structure update
    return {"manager_decision": decision.model_dump()}