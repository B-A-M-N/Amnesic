from typing import Dict, Any, Optional, Callable, List
from ..drivers.ollama import OllamaDriver
from ..presets.code_agent import ManagerMove, FrameworkState
from ..core.pager import Pager
from ..core.memory import compress_history
from ..core.policies import KernelPolicy
from .prompt_builder import ManagerPromptBuilder

class Manager:
    def __init__(self, driver: OllamaDriver, elastic_mode: bool = False, policies: List[KernelPolicy] = []):
        self.driver = driver
        self.elastic_mode = elastic_mode
        self.policies = sorted(policies, key=lambda p: p.priority, reverse=True)

    def decide(self, state: FrameworkState, file_map: list, pager: Optional[Pager] = None, active_context: str = "", l2_list: list = [], stream_callback: Optional[Callable] = None, history_block: str = "", forbidden_tools: List[str] = []) -> ManagerMove:
        """
        The Brain: Deliberates on the next step.
        """
        # --- 0. POLICY ENGINE (Deterministic Override) ---
        last_feedback = state.last_action_feedback or ""
        for policy in self.policies:
            if policy.condition(state):
                # ANTI-LOOP: If this policy's name was in the last feedback as a rejection, skip it.
                if f"[{policy.name}]" in last_feedback and "REJECTED" in last_feedback.upper():
                    continue

                reaction = policy.reaction(state)
                if reaction:
                    # Inject policy name for loop detection
                    reaction.policy_name = policy.name
                    print(f"[{policy.name}] Policy Triggered -> {reaction.tool_call}")
                    return reaction

        # Define Elastic vs Strict Rules
        if self.elastic_mode:
            amnesia_rule = "MODE: ELASTIC. You are allowed to stage multiple files simultaneously. Use 'unstage_context' only when necessary to free up tokens."
            eviction_rule = "Memory pressure is handled automatically."
        else:
            amnesia_rule = "MODE: STRICT AMNESIA (One-File Limit). You MUST finish with the current file (Save Artifact -> Unstage) BEFORE opening a new one."
            eviction_rule = "L1 IS FULL. To read a new file, you MUST unstage the current one first."

        # 1. Update MMU Clock
        if pager:
            pager.tick()
            l1_view = pager.render_context()
            l2_view = list(pager.swap_disk.keys())
        else:
            l1_view = active_context
            l2_view = l2_list
        
        # 2. Prepare Data for Builder
        # MASK ENVIRONMENT IF RESTRICTED (Prevents hallucinating past disk state)
        effective_map = [] if forbidden_tools else file_map
        map_summary = ManagerPromptBuilder.format_map_summary(effective_map)
        
        l1_files = []
        if pager:
            for page in pager.active_pages.values():
                name = page.id.replace("FILE:", "")
                if page.pinned:
                    name += " (PINNED: CANNOT UNSTAGE)"
                l1_files.append(name)
        else:
            l1_files = [active_context] if active_context else []

        l2_files = [f.replace("FILE:", "") for f in (l2_list if not pager else list(pager.swap_disk.keys()))]
        
        # Render ACTUAL content for the prompt
        active_content = pager.render_context() if pager else active_context

        # Format artifacts for prompt
        found_artifacts = [f"{a.identifier}: {a.summary}" for a in state.artifacts]
        artifacts_summary = ", ".join(found_artifacts) if found_artifacts else "None"
        
        # CRITICAL: L1 OCCUPANCY WARNING
        l1_warning = ""
        user_files_staged = [f.replace("FILE:", "").strip() for f in pager.active_pages.keys() if "SYS:" not in f] if pager else []
        
        if user_files_staged:
            l1_warning = f"""
        [CRITICAL: L1 RAM IS OCCUPIED]
        The user file {user_files_staged} is ALREADY OPEN. 
        - DO NOT use 'stage_context' for this file.
        - READ the content below in [CURRENT L1 CONTEXT CONTENT].
        - IF you have not already saved its data, use 'save_artifact' NOW.
        - IF you are finished with it, you MUST 'unstage_context' to free L1.
        """
        elif not l1_files or (len(l1_files) == 1 and "MISSION" in l1_files[0]):
             l1_warning = "\n        [NOTICE: L1 RAM IS EMPTY]. You must 'stage_context' a file to see data."

        # Prepare critical feedback block
        feedback_alert = ""
        if state.last_action_feedback:
            feedback_msg = state.last_action_feedback
            if "LOOP DETECTED" in feedback_msg or "STALEMATE" in feedback_msg:
                feedback_alert = f"\n\n[SYSTEM ALERT - URGENT]: YOU ARE LOOPING. The last action was REJECTED. DO NOT TRY IT AGAIN. {feedback_msg}\nCHANGE STRATEGY IMMEDIATELY."
            else:
                feedback_alert = f"\n\n[SYSTEM ALERT]: {feedback_msg}\n"

        # 3. Construct Prompts
        system_prompt = ManagerPromptBuilder.build_system_prompt(
            state=state,
            l1_files=l1_files,
            l2_files=l2_files,
            artifacts_summary=artifacts_summary,
            feedback_alert=feedback_alert,
            amnesia_rule=amnesia_rule,
            eviction_rule=eviction_rule,
            forbidden_tools=forbidden_tools
        )
        
        user_prompt = ManagerPromptBuilder.build_user_prompt(
            state=state,
            artifacts_summary=artifacts_summary,
            l1_files=l1_files,
            l1_warning=l1_warning,
            feedback_alert=feedback_alert,
            map_summary=map_summary,
            history_block=history_block,
            active_content=active_content
        )
        
        try:
            decision_model = self.driver.generate_structured_with_stream(
                user_prompt=user_prompt, 
                schema=ManagerMove,
                system_prompt=system_prompt,
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