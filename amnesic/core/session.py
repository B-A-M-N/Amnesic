import os
import logging
import copy
import re
from typing import Optional, List, Tuple, TypedDict, Annotated, Union, Any, Dict
from rich.console import Console
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from amnesic.drivers.factory import get_driver
from amnesic.core.environment import ExecutionEnvironment
from amnesic.core.dynamic_pager import DynamicPager
from amnesic.core.comparator import Comparator
from amnesic.core.sidecar import SharedSidecar
from amnesic.decision.manager import Manager, ManagerMove
from amnesic.decision.auditor import Auditor
from amnesic.decision.worker import Worker
from amnesic.core.tool_registry import ToolRegistry
from amnesic.core.policies import KernelPolicy, DEFAULT_COMPLETION_POLICY, CRITICAL_ERROR_POLICY
from amnesic.presets.code_agent import FrameworkState, Artifact
from amnesic.core.memory import compress_history

# --- 1. Define LangGraph State ---
class AgentState(TypedDict):
    framework_state: FrameworkState
    active_file_map: List[Dict[str, Any]]
    manager_decision: Optional[ManagerMove]
    last_audit: Optional[dict] 
    tool_output: Optional[str]
    last_node: Optional[str]

class AmnesicSession:
    def __init__(self, 
                 mission: str = "TASK: Default Mission.", 
                 root_dir: Union[str, List[str]] = ".", 
                 model: str = "rnj-1:8b-cloud", 
                 provider: str = "ollama",
                 l1_capacity: int = 4000,
                 sidecar: Optional[SharedSidecar] = None,
                 deterministic_seed: int = None,
                 strategy: str = None,
                 api_key: str = None,
                 base_url: str = None,
                 elastic_mode: bool = False,
                 sandbox: bool = False,
                 policies: List[KernelPolicy] = []):
        
        self.mission = mission
        self.sandbox = sandbox
        self.shadow_fs = {} 
        if isinstance(root_dir, str):
            self.root_dirs = [os.path.abspath(root_dir)]
        else:
            self.root_dirs = [os.path.abspath(rd) for rd in root_dir]
            
        self.elastic_mode = elastic_mode
        self.console = Console()
        
        driver_kwargs = {"num_ctx": l1_capacity}
        if deterministic_seed is not None:
            driver_kwargs["temperature"] = 0.0
            driver_kwargs["seed"] = deterministic_seed
        else:
            # Default temperature for non-deterministic sessions
            driver_kwargs["temperature"] = 0.1
        
        self.driver = get_driver(provider, model, api_key=api_key, base_url=base_url, **driver_kwargs)
        
        self.env = ExecutionEnvironment(root_dirs=self.root_dirs)
        self.pager = DynamicPager(capacity_tokens=l1_capacity)
        self.comparator = Comparator(self.pager)
        self.pager.pin_page("SYS:MISSION", f"MISSION: {mission}")
        self.sidecar = sidecar 
        
        active_policies = [DEFAULT_COMPLETION_POLICY, CRITICAL_ERROR_POLICY] + policies
        self.manager_node = Manager(self.driver, elastic_mode=elastic_mode, policies=active_policies)
        self.auditor_node = Auditor(goal=mission, constraints=["NO_DELETES"], driver=self.driver, elastic_mode=elastic_mode)
        
        self.tools = ToolRegistry()
        self._setup_default_tools()
        
        self.checkpointer = MemorySaver()
        
        self.state = {
            "framework_state": FrameworkState(
                task_intent=mission,
                current_hypothesis="Initial Assessment",
                hard_constraints=["Local Only"],
                plan=[],
                artifacts=[],
                confidence_score=0.5,
                unknowns=["Context Structure"],
                strategy=strategy,
                elastic_mode=elastic_mode
            ),
            "active_file_map": [],
            "manager_decision": None,
            "last_audit": None,
            "last_node": None
        }
        
        self.app = self._build_graph()

    def run(self, config: dict = None):
        cfg = config or {"configurable": {"thread_id": "default"}}
        for event in self.app.stream(self.state, config=cfg):
            pass

    def _safe_path(self, path: str) -> str:
        target = os.path.abspath(path)
        is_safe = any(target.startswith(rd) for rd in self.root_dirs)
        if not is_safe:
            for rd in self.root_dirs:
                rel_target = os.path.abspath(os.path.join(rd, path))
                if rel_target.startswith(rd):
                    target = rel_target
                    is_safe = True
                    break
        if not is_safe:
            raise PermissionError(f"Path Traversal Blocked: {path}")
        sensitive = [".env", ".git", ".gemini"]
        if any(s in path for s in sensitive):
            raise PermissionError(f"Security Blocked: {path}")
        return target

    def visualize(self):
        try:
            print("\n[Amnesic Kernel Architecture]")
            print(self.app.get_graph().draw_ascii())
            print("\n[Flow Legend]\n1. Manager (CPU)\n2. Auditor (Sec)\n3. Executor (I/O)\n")
        except Exception: pass

    def query(self, question: str, config: dict = None) -> str:
        cfg = config or {"configurable": {"thread_id": "default"}}
        current_state = self.app.get_state(cfg).values or self.state
        fw_state = current_state.get('framework_state')
        fw_state.current_hypothesis = f"QUERY: {question}"
        
        if self.sidecar:
            shared = self.sidecar.get_all_knowledge()
            for k, v in shared.items():
                if not any(a.identifier == k for a in fw_state.artifacts):
                    fw_state.artifacts.append(Artifact(identifier=k, type="config", summary=str(v), status="verified_invariant"))
        
        active_content = self.pager.render_context()
        move = self.manager_node.decide(
            state=fw_state, file_map=self.env.refresh_substrate(),
            pager=self.pager, history_block=f"[QUERY MODE]\nAnswer the following question using your persistent artifacts: {question}",
            active_context=active_content
        )
        return move.thought_process

    def snapshot_state(self, label: str) -> str:
        if not hasattr(self, "_snapshots"): self._snapshots = {}
        self._snapshots[label] = {
            "artifacts": copy.deepcopy(self.state['framework_state'].artifacts),
            "l1_context": copy.deepcopy(self.pager.active_pages)
        }
        return label

    def restore_state(self, snapshot_id: str):
        if hasattr(self, "_snapshots") and snapshot_id in self._snapshots:
            snap = self._snapshots[snapshot_id]
            self.state['framework_state'].artifacts = copy.deepcopy(snap["artifacts"])
            self.pager.active_pages.clear()
            self.pager.active_pages.update(copy.deepcopy(snap["l1_context"]))
            self.state['framework_state'].decision_history = []
            self.state['framework_state'].current_hypothesis = f"RESTORED: {snapshot_id}"

    def _setup_default_tools(self):
        self.tools.register_tool("stage_context", self._tool_stage)
        self.tools.register_tool("unstage_context", self._tool_unstage)
        self.tools.register_tool("save_artifact", self._tool_worker_task)
        self.tools.register_tool("delete_artifact", self._tool_delete_artifact)
        self.tools.register_tool("stage_artifact", self._tool_stage_artifact)
        self.tools.register_tool("edit_file", self._tool_edit)
        self.tools.register_tool("write_file", self._tool_write_file)
        self.tools.register_tool("calculate", self._tool_calculate)
        self.tools.register_tool("verify_step", self._tool_verify_step)
        self.tools.register_tool("compare_files", self._tool_compare_files)
        self.tools.register_tool("switch_strategy", self._tool_switch_strategy)
        self.tools.register_tool("halt_and_ask", lambda target, **kwargs: None)

    def _tool_delete_artifact(self, target: str):
        self.state['framework_state'].artifacts = [a for a in self.state['framework_state'].artifacts if a.identifier != target]
        if self.sidecar: self.sidecar.delete_knowledge(target)
        self.state['framework_state'].last_action_feedback = f"Artifact {target} DELETED."

    def _tool_stage_artifact(self, target: str):
        found = next((a for a in self.state['framework_state'].artifacts if a.identifier == target), None)
        if found:
            self.pager.request_access(f"FILE:ARTIFACT:{target}", found.summary, priority=10)
            self.state['framework_state'].last_action_feedback = f"Artifact {target} staged."
        else: self.state['framework_state'].last_action_feedback = f"Error: Artifact {target} not found."

    def _tool_switch_strategy(self, target: str):
        self.state['framework_state'].strategy = target
        self.state['framework_state'].last_action_feedback = f"Strategy: {target}"

    def _tool_compare_files(self, target: str):
        # Support both comma and space separators
        parts = re.split(r'[,\s]+', target.strip())
        if len(parts) < 2:
            self.state['framework_state'].last_action_feedback = "Compare Failed: Use 'file_a, file_b'"
            return
            
        file_a, file_b = parts[0], parts[1]
        content_a = content_b = ""
        
        # Resolve paths
        try:
            path_a = self._safe_path(file_a)
            path_b = self._safe_path(file_b)
            
            if os.path.exists(path_a): 
                with open(path_a) as f: content_a = f.read()
            if os.path.exists(path_b):
                with open(path_b) as f: content_b = f.read()
                
            if self.comparator.load_pair(file_a, content_a, file_b, content_b):
                worker = Worker(self.driver)
                # Mission-aware merging
                task = f"Merge {file_a} and {file_b}. RECONCILE DIFFERENCES: Ensure BOTH the bug fix (e.g. division by zero check) and the new feature (e.g. multiplication) are preserved in the final code."
                result = worker.execute_task(task, self.pager.render_context(), ["Merged code only.", "No markdown code fences."])
                
                # Use a clear name for the merged result
                self.state['framework_state'].artifacts.append(Artifact(identifier="RESOLVED_CODE", type="code_file", summary=result.content.strip(), status="verified_invariant"))
                self.comparator.purge_pair()
                self.state['framework_state'].last_action_feedback = "SUCCESS: Files compared. artifact 'RESOLVED_CODE' created with merged content. Use 'write_file' to save it to 'resolved.py'."
            else:
                self.state['framework_state'].last_action_feedback = "Compare Failed: Could not load files into Comparator."
        except Exception as e:
            self.state['framework_state'].last_action_feedback = f"Compare Error: {str(e)}"

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("manager", self._node_manager)
        workflow.add_node("auditor", self._node_auditor)
        workflow.add_node("executor", self._node_executor)
        workflow.set_entry_point("manager")
        workflow.add_edge("manager", "auditor")
        def router(state):
            # Terminate if Auditor halts or if Manager halts successfully
            if state['last_audit']['auditor_verdict'] == "HALT": return END
            if state['last_audit']['auditor_verdict'] == "PASS" and state['manager_decision'].tool_call == "halt_and_ask": return END
            return "executor"
        workflow.add_conditional_edges("auditor", router, {"executor": "executor", END: END})
        workflow.add_edge("executor", "manager")
        return workflow.compile(checkpointer=self.checkpointer)

    def _node_manager(self, state: AgentState):
        print(f"DEBUG: Manager received state. Feedback: {state['framework_state'].last_action_feedback}")
        self.pager.tick()
        current_map = self.env.refresh_substrate()
        
        # Physical Garbage Collection: If a file was deleted or is no longer in the map, 
        # it should probably be removed from L1 to prevent hallucination.
        valid_paths = [os.path.basename(f['path']) for f in current_map]
        active_keys = list(self.pager.active_pages.keys())
        for k in active_keys:
            if "SYS:" in k: continue
            clean_k = k.replace("FILE:", "")
            if clean_k not in valid_paths:
                print(f"         Kernel: Physical GC - Removing {clean_k} (Missing from substrate)")
                del self.pager.active_pages[k]

        active_pages = [p.replace("FILE:", "") for p in self.pager.active_pages.keys() if "SYS:" not in p]
        l1_status = f"L1 RAM CONTENT: {', '.join(active_pages) if active_pages else 'EMPTY'}"
        if self.sidecar:
            shared = self.sidecar.get_all_knowledge()
            for k, v in shared.items():
                if not any(a.identifier == k for a in state['framework_state'].artifacts):
                    state['framework_state'].artifacts.append(Artifact(identifier=k, type="config", summary=str(v), status="verified_invariant"))
        history = state['framework_state'].decision_history
        history_lines = [f"Turn {i}: {h.get('tool_call', 'unknown')} -> {h['auditor_verdict']}" for i, h in enumerate(history)]
        history_block = "[HISTORY]\n" + compress_history(history_lines, max_turns=10)
        move = self.manager_node.decide(state=state['framework_state'], file_map=current_map, pager=self.pager, history_block=history_block, active_context=l1_status)
        
        print(f"[Turn {len(history)+1}] Manager: {move.tool_call}({move.target})")
        return {"manager_decision": move, "active_file_map": current_map, "last_node": "manager"}

    def _node_auditor(self, state: AgentState):
        move = state['manager_decision']
        if move.tool_call in ["stage_context", "edit_file", "write_file"]:
            try: self._safe_path(move.target.split(":", 1)[0].strip() if ":" in move.target else move.target)
            except PermissionError as e:
                audit = {"auditor_verdict": "REJECT", "rationale": str(e)}
                # Ensure turn is recorded correctly in history
                turn = len(state['framework_state'].decision_history) + 1
                state['framework_state'].decision_history.append({"turn": turn, "tool_call": move.tool_call, "target": move.target, "auditor_verdict": "REJECT", "rationale": str(e)})
                return {"last_audit": audit, "framework_state": state['framework_state'], "last_node": "auditor"}
        
        valid_files = [f['path'] for f in state.get('active_file_map', [])]
        active_pages_clean = [p.replace("FILE:", "") for p in self.pager.active_pages.keys()]
        audit = self.auditor_node.evaluate_move(move.tool_call, move.target, move.thought_process, valid_files, active_pages_clean, state['framework_state'].decision_history, state['framework_state'].artifacts, active_context=self.pager.render_context())
        
        print(f"         Auditor: {audit['auditor_verdict']} ({audit['rationale']})")
        
        # Use the actual verdict from evaluation
        turn = len(state['framework_state'].decision_history) + 1
        state['framework_state'].decision_history.append({"turn": turn, "tool_call": move.tool_call, "target": move.target, "auditor_verdict": audit["auditor_verdict"], "rationale": audit["rationale"]})
        return {"last_audit": audit, "framework_state": state['framework_state'], "last_node": "auditor"}

    def _node_executor(self, state: AgentState):
        move = state['manager_decision']
        if state['last_audit']["auditor_verdict"] == "PASS":
            try: 
                print(f"         Executor: Executing {move.tool_call}")
                # Reset feedback before execution to detect if tool updates it
                self.state['framework_state'].last_action_feedback = None
                self.tools.execute(move.tool_call, target=move.target)
                
                # Only set default success if tool didn't set feedback
                if self.state['framework_state'].last_action_feedback is None:
                    self.state['framework_state'].last_action_feedback = f"SUCCESS: {move.tool_call}"
                
                # Update history with execution result
                if state['framework_state'].decision_history:
                    state['framework_state'].decision_history[-1]["execution_result"] = "SUCCESS"
            except Exception as e: 
                print(f"         Executor: ERROR {str(e)}")
                self.state['framework_state'].last_action_feedback = f"ERROR: {str(e)}"
                # Update history with execution failure
                if state['framework_state'].decision_history:
                    state['framework_state'].decision_history[-1]["execution_result"] = f"ERROR: {str(e)}"
                    state['framework_state'].decision_history[-1]["auditor_verdict"] = "FAILED_EXECUTION"
        else: 
            self.state['framework_state'].last_action_feedback = f"REJECTED: {state['last_audit']['rationale']}"
            if state['framework_state'].decision_history:
                state['framework_state'].decision_history[-1]["execution_result"] = "NOT_EXECUTED"
        
        return {"framework_state": self.state['framework_state'], "last_node": "executor"}

    def _tool_stage(self, target: str):
        # Handle multiple paths or quoted paths
        targets = [t.strip().strip("'").strip('"').strip('`') for t in target.replace(',', ' ').split()]
        for file_path in targets:
            try:
                l1_key = os.path.basename(file_path)
                safe_target = self._safe_path(file_path)
                content = None
                if self.sandbox and safe_target in self.shadow_fs: 
                    content = self.shadow_fs[safe_target]
                elif os.path.exists(safe_target):
                    with open(safe_target, 'r', errors='replace') as f: 
                        content = f.read()
                
                if content is not None:
                    if not self.pager.request_access(f"FILE:{l1_key}", content, priority=8): 
                        raise ValueError(f"L1 Full: Cannot stage {l1_key}")
                    self.state['framework_state'].last_action_feedback = f"SUCCESS: Staged {l1_key}"
                else:
                    self.state['framework_state'].last_action_feedback = f"CRITICAL ERROR: File '{file_path}' NOT FOUND on disk. It is missing from the environment."
            except Exception as e: 
                self.state['framework_state'].last_action_feedback = f"ERROR: {str(e)}"

    def _tool_unstage(self, target: str):
        clean = target.strip("'").strip('"')
        l1_key = os.path.basename(clean)
        if f"FILE:{l1_key}" in self.pager.active_pages:
            self.pager.evict_to_l2(f"FILE:{l1_key}")
            self.state['framework_state'].last_action_feedback = f"Unstaged {l1_key}"

    def _tool_worker_task(self, target: str):
        active_context = self.pager.render_context()
        worker = Worker(self.driver)
        
        # 1. Extract Identifier (Handle KEY=VALUE or KEY: VALUE formats)
        identifier = target
        if "=" in target:
            identifier = target.split("=", 1)[0].strip()
        elif ":" in target and not target.startswith("http"): 
            identifier = target.split(":", 1)[0].strip()
        
        # 1.1 SYMBOLIC NORMALIZATION
        # If the model sends "The value is X", we prune it to "THE_VALUE_IS_X" or similar, 
        # or better: we take only the first word if it looks like a symbol.
        # But if it's prose, we should ideally fail or take a "slugified" version.
        if " " in identifier:
             # Take the last word if it's the target, or first if it's a key.
             # Actually, let's just slugify to prevent validation errors while preserving intent.
             identifier = re.sub(r'[^a-zA-Z0-9_.-]', '_', identifier).strip('_')
             # Limit length
             identifier = identifier[:64]
        
        # 2. Special handling for Mission Completion
        if "TOTAL" in target.upper() or "TOTAL" in identifier.upper():
            identifier = "TOTAL"
            # Combine all existing artifacts into context for the worker
            arts_context = "\n".join([f"{a.identifier}: {a.summary}" for a in self.state['framework_state'].artifacts])
            result = worker.execute_task(f"Combine all parts into the final sentence: {target}", active_context + "\n" + arts_context, ["Raw sentence only."])
            self.state['framework_state'].current_hypothesis = result.content
        else:
            # Check if artifact already exists with exact same data to prevent loops
            # Relaxed for non-elastic mode to allow file evictions
            existing = next((a for a in self.state['framework_state'].artifacts if a.identifier == identifier), None)
            result = worker.execute_task(f"Extract {target}", active_context, ["Raw value only."])
            
            if self.elastic_mode and existing and existing.summary.strip() == result.content.strip():
                self.state['framework_state'].last_action_feedback = f"Artifact {identifier} already contains this data. Mission progressing."
                return

        # 3. Save Artifact (Replacing existing with same identifier)
        self.state['framework_state'].artifacts = [a for a in self.state['framework_state'].artifacts if a.identifier != identifier]
        self.state['framework_state'].artifacts.append(Artifact(identifier=identifier, type="text_content", summary=result.content, status="verified_invariant"))
        if self.sidecar: self.sidecar.ingest_knowledge(identifier, result.content)
        
        # Only evict if NOT in elastic mode
        if not self.elastic_mode:
            for fid in [p for p in self.pager.active_pages.keys() if "FILE:" in p]: self.pager.evict_to_l2(fid)
        self.state['framework_state'].last_action_feedback = f"Artifact {identifier} saved."

    def _tool_write_file(self, target: str):
        path = content = ""
        if ":" in target:
            path, content = target.split(":", 1)
        elif "," in target:
            parts = [p.strip().strip("'").strip('"') for p in target.split(",")]
            path = parts[0]
            content = ", ".join(parts[1:])
        else: 
            self.state['framework_state'].last_action_feedback = "Write Failed: Use 'path: content'"
            return
        
        path = path.strip()
        content = content.strip()
        
        # ARTIFACT LOOKUP: If content is ARTIFACT:key, pull from artifacts
        if content.startswith("ARTIFACT:"):
            art_key = content.replace("ARTIFACT:", "").strip()
            found = next((a for a in self.state['framework_state'].artifacts if a.identifier == art_key), None)
            if found:
                content = found.summary
            else:
                self.state['framework_state'].last_action_feedback = f"Write Error: Artifact '{art_key}' not found."
                return

        safe_path = self._safe_path(path)
        with open(safe_path, "w") as f: f.write(content)
        
        # AUTO-SAVE ARTIFACT: Ensure Auditor sees this as a completed requirement
        identifier = os.path.basename(path)
        self.state['framework_state'].artifacts = [a for a in self.state['framework_state'].artifacts if a.identifier != identifier]
        self.state['framework_state'].artifacts.append(Artifact(identifier=identifier, type="code_file", summary=content, status="committed"))
        self.state['framework_state'].last_action_feedback = f"SUCCESS: File {identifier} written and saved as artifact."

    def _tool_edit(self, target: str):
        file_path = instruction = ""
        
        # 1. Surgical Split: Handle 'path: instruction'
        if ":" in target:
            parts = target.split(":", 1)
            file_path = parts[0].strip().strip("'").strip('"').strip('`')
            instruction = parts[1].strip()
            
            # 2. Signature Stripping from Instruction: 
            # If instruction starts with a signature (def login...), strip it
            # because models often repeat the signature they are trying to fix.
            if any(instruction.startswith(kw) for kw in ["def ", "class "]):
                # If there's a newline, the instruction might be the whole block
                # but if there's no newline, they just put the signature.
                if "\n" not in instruction:
                    # Treat the signature as the instruction (it will be passed to Worker)
                    pass 
        
        # 3. Newline Split Strategy (Fallback/Robustness for LLM blocks)
        if not file_path and "\n" in target:
            lines = target.split("\n")
            potential_path = lines[0].strip().rstrip(":").strip("'").strip('"').strip('`')
            if len(potential_path) < 100 and ("." in potential_path or "/" in potential_path):
                file_path = potential_path
                instruction = "\n".join(lines[1:])
        
        # 4. Standard splitting fallbacks
        if not file_path:
            if "," in target:
                parts = [p.strip().strip("'").strip('"').strip('`') for p in target.split(",")]
                file_path = parts[0]
                instruction = ", ".join(parts[1:])
            else:
                self.state['framework_state'].last_action_feedback = "Edit Failed: Use 'path: instruction'"
                return

        file_path = file_path.strip().strip("'").strip('"').strip('`')
        safe_path = ""
        try:
            safe_path = self._safe_path(file_path.strip())
        except Exception:
            pass
        
        # AUTO-DISCOVERY: If path doesn't exist, try to find it in the substrate by basename
        if not safe_path or not os.path.exists(safe_path):
            basename = os.path.basename(file_path)
            for fmap in self.state.get('active_file_map', []):
                if os.path.basename(fmap['path']) == basename:
                    file_path = fmap['path']
                    safe_path = self._safe_path(file_path)
                    print(f"         Executor: Auto-resolved '{basename}' to '{file_path}'")
                    break

        # AST LOOKUP: If still not found, check if it's a function/class name
        if not safe_path or not os.path.exists(safe_path):
            symbol_name = file_path.strip().split('(')[0].replace('def ', '').replace('class ', '').strip()
            found_paths = []
            
            if 'active_file_map' in self.state:
                for fmap in self.state['active_file_map']:
                    # Check path match
                    if symbol_name in fmap['path']:
                        found_paths.append(fmap['path'])
                        continue
                    # Check functions
                    for func in fmap.get('functions', []):
                        if func['name'] == symbol_name:
                            found_paths.append(fmap['path'])
                    # Check classes
                    for cls in fmap.get('classes', []):
                        if cls['name'] == symbol_name:
                            found_paths.append(fmap['path'])
            
            if len(found_paths) >= 1:
                # If we found multiple, pick the first one that is currently in L1 if possible
                l1_keys = [p.replace("FILE:", "") for p in self.pager.active_pages.keys()]
                best_path = found_paths[0]
                for p in found_paths:
                    if os.path.basename(p) in l1_keys:
                        best_path = p
                        break
                
                print(f"         Executor: Auto-resolved '{symbol_name}' to file '{best_path}'")
                file_path = best_path
                safe_path = self._safe_path(file_path)
            elif not safe_path:
                 # If we still have nothing, re-raise original or set error
                 self.state['framework_state'].last_action_feedback = f"Edit Failed: File {file_path} not found and could not be resolved."
                 return

        result = Worker(self.driver).perform_edit(file_path.strip(), instruction.strip(), self.pager.render_context(), ["Indent preservation."])
        content = self.shadow_fs.get(safe_path) if self.sandbox else None
        if content is None and os.path.exists(safe_path):
            with open(safe_path, 'r') as f: content = f.read()
        
        if content:
            # DEBUG: Match diagnostics
            safe_content = content[:100].replace('\n', '\\n')
            safe_snippet = result.original_snippet[:100].replace('\n', '\\n')
            print(f"         DEBUG Executor: Target File Content (first 100 chars): [{safe_content}]")
            print(f"         DEBUG Executor: Original Snippet (first 100 chars): [{safe_snippet}]")
            
            # 1. Try Exact Match First
            if result.original_snippet in content:
                new_content = content.replace(result.original_snippet, result.new_snippet)
            else:
                # 2. Try Regex Match (Fuzzy whitespace)
                # Escape the snippet then allow for whitespace variations
                escaped = re.escape(result.original_snippet)
                pattern = re.sub(r'\\s+', r'\\s*', escaped) # Collapse whitespace
                match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
                
                if match:
                    print(f"         DEBUG Executor: Regex match successful.")
                    new_content = content[:match.start()] + result.new_snippet + content[match.end():]
                else:
                    # Final attempt: try matching by collapsing all whitespace in both
                    collapsed_content = re.sub(r'\s+', '', content)
                    collapsed_snippet = re.sub(r'\s+', '', result.original_snippet)
                    
                    if collapsed_snippet in collapsed_content:
                         print(f"         DEBUG Executor: Collapsed match found. Attempting super-fuzzy regex.")
                         # Still need to know WHERE to replace, so regex is better
                         # Let's try an even fuzzier regex
                         fuzzy_pattern = re.escape(result.original_snippet)
                         fuzzy_pattern = re.sub(r'\\ ', r'\\s*', fuzzy_pattern)
                         fuzzy_pattern = re.sub(r'\\n', r'\\s*', fuzzy_pattern)
                         fuzzy_match = re.search(fuzzy_pattern, content, re.MULTILINE | re.DOTALL)
                         if fuzzy_match:
                              new_content = content[:fuzzy_match.start()] + result.new_snippet + content[fuzzy_match.end():]
                         else:
                              self.state['framework_state'].last_action_feedback = f"Edit Failed: Snippet not found in file '{file_path}'. Formatting mismatch."
                              return
                    else:
                        print(f"         DEBUG Executor: Snippet not found even with collapsed whitespace.")
                        self.state['framework_state'].last_action_feedback = f"Edit Failed: Snippet not found in file '{file_path}'. Check logic."
                        return

            if self.sandbox: self.shadow_fs[safe_path] = new_content
            else:
                with open(safe_path, 'w') as f: f.write(new_content)
            
            l1_key = os.path.basename(file_path.strip())
            if f"FILE:{l1_key}" in self.pager.active_pages: 
                self.pager.request_access(f"FILE:{l1_key}", new_content)
            
            self.state['framework_state'].last_action_feedback = f"SUCCESS: Edited {file_path}"
        else:
            self.state['framework_state'].last_action_feedback = f"Edit Failed: File {file_path} not found."

    def _tool_verify_step(self, target: str):
        # Hybrid: If it looks like math, calculate. Else, verify presence in L1.
        # Use regex for whole-word operator matching to avoid false positives (e.g., 'Add' in 'Address')
        math_operators = ["ADD", "SUBTRACT", "MULTIPLY", "DIVIDE"]
        has_math_pattern = re.search(r'[\d+\-*/]', target)
        has_explicit_op = any(re.search(rf'\b{op}\b', target.upper()) for op in math_operators)
        
        if has_math_pattern or has_explicit_op:
             self._tool_calculate(target)
             return

        context = self.pager.render_context()
        # If target looks like a filename (has extension), check physical disk via substrate
        if "." in target and (target.endswith(".py") or target.endswith(".txt")):
            current_map = self.env.refresh_substrate()
            valid_paths = [os.path.basename(f['path']) for f in current_map]
            found = target in valid_paths
        else:
            # Fallback to content check
            found = target in context
            
        status = "PASSED" if found else "FAILED"
        # Note matching output format for test_contracts_unit
        summary = f"Verification {status}: '{target}' verified." if found else f"Verification {status}: NOTE: '{target}' not found."
        
        self.state['framework_state'].artifacts = [a for a in self.state['framework_state'].artifacts if a.identifier != "VERIFICATION"]
        self.state['framework_state'].artifacts.append(Artifact(identifier="VERIFICATION", type="result", summary=summary, status="committed"))
        self.state['framework_state'].last_action_feedback = summary

    def _tool_calculate(self, target: str):
        # 1. Try to extract numbers from the target command first (Explicit arguments)
        nums = [int(n) for n in re.findall(r'\d+', target)]
        
        # 2. If no numbers in target, fallback to context (Implicit arguments from Artifacts)
        if not nums:
            arts = self.state['framework_state'].artifacts
            summary = " ".join([a.summary for a in arts])
            nums = [int(n) for n in re.findall(r'\d+', summary)]
            
        # Combine check string for operation detection
        # (We still check target + summary for keywords like "MULTIPLY" just in case the keyword is in the artifacts? 
        # Actually, usually the operation is in the target command. Let's keep it simple and check target first, then artifacts)
        check_str = target + " " + " ".join([a.summary for a in self.state['framework_state'].artifacts])

        res = 0
        op = "ADD"
        if "*" in target or "MULTIPLY" in check_str.upper(): 
            op = "MULTIPLY"
            if nums:
                res = 1
                for n in nums: res *= n
        elif "/" in target or "DIVIDE" in check_str.upper(): 
            op = "DIVIDE"
            if len(nums) > 1:
                res = nums[0]
                for n in nums[1:]:
                    if n == 0:
                        res_str = "Error: Division by zero"
                        self.state['framework_state'].last_action_feedback = res_str
                        self.state['framework_state'].artifacts.append(Artifact(identifier="TOTAL", type="error_log", summary=res_str, status="needs_review"))
                        return
                    res /= n
            elif nums:
                res = nums[0]
        elif "-" in target or "SUBTRACT" in check_str.upper(): 
            op = "SUBTRACT"
            res = nums[0] - sum(nums[1:]) if len(nums) > 1 else (nums[0] if nums else 0)
        else: 
            # Default to ADD
            res = sum(nums)

        res_str = f"Final ({op}): {res}"
        self.state['framework_state'].artifacts = [a for a in self.state['framework_state'].artifacts if a.identifier != "TOTAL"]
        self.state['framework_state'].artifacts.append(Artifact(identifier="TOTAL", type="result", summary=res_str, status="committed"))
        self.state['framework_state'].current_hypothesis = f"MISSION COMPLETE: {res_str}"
