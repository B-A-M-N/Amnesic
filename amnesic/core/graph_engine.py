import os
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from amnesic.core.state import AgentState
from amnesic.decision.manager import Manager
from amnesic.decision.auditor import Auditor
from amnesic.core.memory import compress_history

class GraphEngine:
    def __init__(self, session):
        self.session = session
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("manager", self._node_manager)
        workflow.add_node("auditor", self._node_auditor)
        workflow.add_node("executor", self._node_executor)
        
        workflow.set_entry_point("manager")
        workflow.add_edge("manager", "auditor")
        
        def router(state):
            if state['last_audit']['auditor_verdict'] == "HALT": return END
            if state['last_audit']['auditor_verdict'] == "PASS" and state['manager_decision'].tool_call == "halt_and_ask": return END
            return "executor"
            
        workflow.add_conditional_edges("auditor", router, {"executor": "executor", END: END})
        workflow.add_edge("executor", "manager")
        
        return workflow.compile(checkpointer=self.session.checkpointer)

    def _node_manager(self, state: AgentState):
        for attempt in range(2):
            try:
                # 0. ELASTIC CAPACITY UPDATE
                self.session.recalculate_pager_capacity(state)
                
                self.session.pager.tick()
                current_map = self.session.env.refresh_substrate()
                
                # Physical Garbage Collection
                valid_paths = [os.path.basename(f['path']) for f in current_map]
                active_keys = list(self.session.pager.active_pages.keys())
                for k in active_keys:
                    if "SYS:" in k: continue
                    if "FILE:ARTIFACT:" in k: continue
                    
                    clean_k = k.replace("FILE:", "")
                    if clean_k not in valid_paths:
                        del self.session.pager.active_pages[k]

                active_pages = [p.replace("FILE:", "") for p in self.session.pager.active_pages.keys() if "SYS:" not in p]
                l1_status = f"L1 RAM CONTENT: {', '.join(active_pages) if active_pages else 'EMPTY'}"
                
                # --- Context Visualization ---
                curr = self.session.pager.current_usage
                cap = self.session.pager.capacity
                pct = (curr / cap) * 100 if cap > 0 else 0
                
                # Fancy Bar
                bar_len = 25
                fill = int(bar_len * (pct / 100))
                bar = "━" * fill + "─" * (bar_len - fill)
                
                color = "green"
                if pct > 80: color = "red"
                elif pct > 50: color = "yellow"
                
                # Print standardized header for the turn
                print(f"\n[{pct:5.1f}%] [{color}]{bar}[/{color}] ({curr}/{cap}) | L1: {active_pages}")
                
                last_feedback = state['framework_state'].last_action_feedback
                if last_feedback:
                    print(f"Feedback: {last_feedback}")

                # --- STATE DELTA GOVERNANCE ---
                state_fingerprint = f"{[a.identifier for a in state['framework_state'].artifacts if a]}|{active_pages}"
                
                last_feedback = state['framework_state'].last_action_feedback or ""
                
                # Tool Failure Acceleration: If we see a syntax error in feedback, accelerate stagnation
                is_tool_failure = "Failed" in last_feedback or "Syntax" in last_feedback or "ERROR" in last_feedback
                
                if not hasattr(self, "_last_state_fingerprint"):
                    self._last_state_fingerprint = state_fingerprint
                    self._stagnation_counter = 0
                
                if state_fingerprint == self._last_state_fingerprint:
                    self._stagnation_counter += (2 if is_tool_failure else 1)
                else:
                    self._last_state_fingerprint = state_fingerprint
                    self._stagnation_counter = 0
                    
                if self._stagnation_counter >= 3:
                    print(f"         Kernel: STATE DELTA ZERO ({'Tool Failure' if is_tool_failure else 'Static State'}). Wiping history.")
                    state['framework_state'].decision_history = state['framework_state'].decision_history[-1:]
                    self._stagnation_counter = 0

                if self.session.sidecar:
                    shared = self.session.sidecar.get_all_knowledge()
                    for k, v in shared.items():
                        if k in ["TOTAL", "VERIFICATION"]:
                            continue
                            
                        if not any(a and a.identifier == k for a in state['framework_state'].artifacts):
                            from amnesic.presets.code_agent import Artifact
                            state['framework_state'].artifacts.append(Artifact(identifier=k, type="config", summary=str(v), status="verified_invariant"))
                
                history = state['framework_state'].decision_history
                history_lines = [f"[TURN {i}] Action: {h.get('tool_call', 'unknown')} | Status: {h['auditor_verdict']}" for i, h in enumerate(history)]
                history_block = "[STRICT DECISION LOG]\n" + compress_history(history_lines, max_turns=10)
                
                # --- DYNAMIC SYNTAX HINTING ---
                last_feedback = state['framework_state'].last_action_feedback or ""
                syntax_hint = ""
                if "Failed" in last_feedback or "Syntax" in last_feedback:
                    if "edit_file" in last_feedback or "edit_file" in str(history[-1:]):
                        syntax_hint = "\n[SYNTAX CORRECTION] 'edit_file' target MUST be 'filename: exact instruction'."
                    elif "save_artifact" in last_feedback:
                        syntax_hint = "\n[SYNTAX CORRECTION] 'save_artifact' target MUST be 'ID_NAME: value'."
                    elif "write_file" in last_feedback:
                        syntax_hint = "\n[SYNTAX CORRECTION] 'write_file' target MUST be 'filename: content'."
                
                feedback_block = f"AUDITOR FEEDBACK: {last_feedback}{syntax_hint}" if last_feedback else "None"
                
                move = self.session.manager_node.decide(
                    state=state['framework_state'], 
                    file_map=current_map, 
                    pager=self.session.pager, 
                    history_block=history_block, 
                    active_context=l1_status,
                    forbidden_tools=state.get('forbidden_tools', []),
                    feedback_override=feedback_block
                )
                
                print(f"[Turn {len(history)+1}] Thought: {move.thought_process}")
                print(f"         Manager: {move.tool_call}({move.target})")
                return {"manager_decision": move, "active_file_map": current_map, "last_node": "manager", "framework_state": state['framework_state']}
                
            except AttributeError as e:
                if "NoneType" in str(e) and "identifier" in str(e):
                    print(f"         Kernel: Recovered from Artifact Corruption ({e}). Scrubbing state.")
                    # Self-healing: Scrub None values
                    if state['framework_state'].artifacts:
                        state['framework_state'].artifacts = [a for a in state['framework_state'].artifacts if a is not None]
                    
                    # If we already retried and failed, FORCE A CALCULATE to try and salvage the mission
                    if attempt > 0:
                        print("         Kernel: Critical Stability Failure. Forcing Emergency Calculation.")
                        from amnesic.decision.manager import ManagerMove
                        return {
                            "manager_decision": ManagerMove(tool_call="calculate", target="SUM_BACKPACK", thought_process="Emergency State Recovery"),
                            "active_file_map": [],
                            "last_node": "manager", 
                            "framework_state": state['framework_state']
                        }
                    continue # Retry the loop
                raise e

    def _node_auditor(self, state: AgentState):
        move = state['manager_decision']
        if move.tool_call in ["stage_context", "edit_file", "write_file"]:
            try: 
                self.session._safe_path(move.target.split(":", 1)[0].strip() if ":" in move.target else move.target)
            except PermissionError as e:
                audit = {"auditor_verdict": "REJECT", "rationale": str(e)}
                # (omitting trace append for brevity, handled by wrapper)
                return {"last_audit": audit, "last_node": "auditor"}
        
        # Inject Active Context for grounding checks
        state['current_context_window'] = self.session.pager.render_context()
        
        # Use the session's auditor_node (wrapper function)
        return self.session.auditor_node(state)

    def _node_executor(self, state: AgentState):
        move = state['manager_decision']
        if state['last_audit']["auditor_verdict"] == "PASS":
            try: 
                print(f"         Executor: Executing {move.tool_call}")
                self.session.state['framework_state'].last_action_feedback = None
                self.session.tools.execute(move.tool_call, target=move.target)
                
                if self.session.state['framework_state'].last_action_feedback is None:
                    self.session.state['framework_state'].last_action_feedback = f"SUCCESS: {move.tool_call}"
                
                if state['framework_state'].decision_history:
                    state['framework_state'].decision_history[-1]["execution_result"] = "SUCCESS"
            except Exception as e: 
                print(f"         Executor: ERROR {str(e)}")
                self.session.state['framework_state'].last_action_feedback = f"ERROR: {str(e)}"
                if state['framework_state'].decision_history:
                    state['framework_state'].decision_history[-1]["execution_result"] = f"ERROR: {str(e)}"
                    state['framework_state'].decision_history[-1]["auditor_verdict"] = "FAILED_EXECUTION"
        else:
            policy_tag = f"[{move.policy_name}] " if getattr(move, 'policy_name', None) else ""
            self.session.state['framework_state'].last_action_feedback = f"{policy_tag}REJECTED: {state['last_audit']['rationale']}"
            if state['framework_state'].decision_history:
                state['framework_state'].decision_history[-1]["execution_result"] = "NOT_EXECUTED"
        
        return {"framework_state": self.session.state['framework_state'], "last_node": "executor"}
