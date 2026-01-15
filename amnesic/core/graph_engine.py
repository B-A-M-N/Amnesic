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
        print(f"DEBUG: Manager received state. Feedback: {state['framework_state'].last_action_feedback}")
        self.session.pager.tick()
        current_map = self.session.env.refresh_substrate()
        
        # Physical Garbage Collection
        valid_paths = [os.path.basename(f['path']) for f in current_map]
        active_keys = list(self.session.pager.active_pages.keys())
        for k in active_keys:
            if "SYS:" in k: continue
            clean_k = k.replace("FILE:", "")
            if clean_k not in valid_paths:
                print(f"         Kernel: Physical GC - Removing {clean_k} (Missing from substrate)")
                del self.session.pager.active_pages[k]

        active_pages = [p.replace("FILE:", "") for p in self.session.pager.active_pages.keys() if "SYS:" not in p]
        l1_status = f"L1 RAM CONTENT: {', '.join(active_pages) if active_pages else 'EMPTY'}"
        
        if self.session.sidecar:
            shared = self.session.sidecar.get_all_knowledge()
            for k, v in shared.items():
                if not any(a.identifier == k for a in state['framework_state'].artifacts):
                    from amnesic.presets.code_agent import Artifact
                    state['framework_state'].artifacts.append(Artifact(identifier=k, type="config", summary=str(v), status="verified_invariant"))
        
        history = state['framework_state'].decision_history
        history_lines = [f"Turn {i}: {h.get('tool_call', 'unknown')} -> {h['auditor_verdict']}" for i, h in enumerate(history)]
        history_block = "[HISTORY]\n" + compress_history(history_lines, max_turns=10)
        
        move = self.session.manager_node.decide(
            state=state['framework_state'], 
            file_map=current_map, 
            pager=self.session.pager, 
            history_block=history_block, 
            active_context=l1_status
        )
        
        print(f"[Turn {len(history)+1}] Manager: {move.tool_call}({move.target})")
        return {"manager_decision": move, "active_file_map": current_map, "last_node": "manager"}

    def _node_auditor(self, state: AgentState):
        move = state['manager_decision']
        if move.tool_call in ["stage_context", "edit_file", "write_file"]:
            try: 
                self.session._safe_path(move.target.split(":", 1)[0].strip() if ":" in move.target else move.target)
            except PermissionError as e:
                audit = {"auditor_verdict": "REJECT", "rationale": str(e)}
                turn = len(state['framework_state'].decision_history) + 1
                state['framework_state'].decision_history.append({"turn": turn, "tool_call": move.tool_call, "target": move.target, "auditor_verdict": "REJECT", "rationale": str(e)})
                return {"last_audit": audit, "framework_state": state['framework_state'], "last_node": "auditor"}
        
        valid_files = [f['path'] for f in state.get('active_file_map', [])]
        active_pages_clean = [p.replace("FILE:", "") for p in self.session.pager.active_pages.keys()]
        
        audit = self.session.auditor_node.evaluate_move(
            move.tool_call, move.target, move.thought_process, 
            valid_files, active_pages_clean, 
            state['framework_state'].decision_history, 
            state['framework_state'].artifacts, 
            active_context=self.session.pager.render_context()
        )
        
        print(f"         Auditor: {audit['auditor_verdict']} ({audit['rationale']})")
        
        turn = len(state['framework_state'].decision_history) + 1
        state['framework_state'].decision_history.append({"turn": turn, "tool_call": move.tool_call, "target": move.target, "auditor_verdict": audit["auditor_verdict"], "rationale": audit["rationale"]})
        return {"last_audit": audit, "framework_state": state['framework_state'], "last_node": "auditor"}

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
