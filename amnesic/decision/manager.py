from typing import Dict, Any, Optional, Callable, List
from ..drivers.ollama import OllamaDriver
from ..presets.code_agent import MANAGER_SYSTEM_PROMPT, ManagerMove, FrameworkState
from ..core.pager import Pager
from ..core.memory import compress_history
from ..core.policies import KernelPolicy

class Manager:
    def __init__(self, driver: OllamaDriver, elastic_mode: bool = False, policies: List[KernelPolicy] = []):
        self.driver = driver
        self.elastic_mode = elastic_mode
        self.policies = sorted(policies, key=lambda p: p.priority, reverse=True)

    def decide(self, state: FrameworkState, file_map: list, pager: Optional[Pager] = None, active_context: str = "", l2_list: list = [], stream_callback: Optional[Callable] = None, history_block: str = "") -> ManagerMove:
        """
        The Brain: Deliberates on the next step.
        """
        # --- 0. POLICY ENGINE (Deterministic Override) ---
        # Checks for automated triggers (Safety, Mission Complete, Events)
        for policy in self.policies:
            if policy.condition(state):
                reaction = policy.reaction(state)
                if reaction:
                    # Log the intervention for transparency
                    print(f"[{policy.name}] Policy Triggered -> {reaction.tool_call}")
                    return reaction

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
            
        # Strategy Injection (Decouples specific test logic from core)
        strategy_block = state.strategy if state.strategy else "1. Focus on the Mission objectives."

        prompt = f"""
        [CRITICAL GROUND TRUTH]
        Completed Artifacts: {artifacts_summary if state.artifacts else "NONE"}
        Current L1 RAM: {l1_files}

        [ENVIRONMENT STRUCTURE]
        {map_summary}

        {history_block}
        
        [CURRENT L1 CONTEXT CONTENT]
        {active_content}

        [DECISION RULES]
        1. IF you have an artifact (e.g. 'X_value'), you MUST NOT stage its source file again.
        2. IF you need a new file and L1 is full (see Current L1 RAM), you MUST use 'unstage_context' first.
        3. IF you have all artifacts required for the mission, you MUST use 'calculate' or 'halt_and_ask'.
        4. TRUST your artifacts. They are your persistent memory.

        [INSTRUCTIONS (Cognitive Load Shaping)]
        {strategy_block}
        {l1_rule_prompt}
        
        {feedback_str}
        
        Decide the next move based on the infrastructure truth.
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