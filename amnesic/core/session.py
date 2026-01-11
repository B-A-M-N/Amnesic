import os
import logging
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
from amnesic.core.policies import KernelPolicy, DEFAULT_COMPLETION_POLICY
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
                 policies: List[KernelPolicy] = []):
        
        self.mission = mission
        # Normalize to list of absolute paths
        if isinstance(root_dir, str):
            self.root_dirs = [os.path.abspath(root_dir)]
        else:
            self.root_dirs = [os.path.abspath(rd) for rd in root_dir]
            
        self.elastic_mode = elastic_mode
        self.console = Console()
        
        # Enforce Determinism if requested
        driver_kwargs = {"num_ctx": l1_capacity}
        if deterministic_seed is not None:
            driver_kwargs["temperature"] = 0.0
            # Note: Seed setting might depend on provider support, but temperature=0 is the big one.
        
        self.driver = get_driver(provider, model, api_key=api_key, base_url=base_url, **driver_kwargs)
        
        # 1. Infrastructure
        self.env = ExecutionEnvironment(root_dirs=self.root_dirs)
        self.pager = DynamicPager(capacity_tokens=l1_capacity)
        self.comparator = Comparator(self.pager)
        self.pager.pin_page("SYS:MISSION", f"MISSION: {mission}")
        self.sidecar = sidecar # Hive Mind connection
        
        # 2. Nodes
        # Policy Injection: Default + User Defined
        active_policies = [DEFAULT_COMPLETION_POLICY] + policies
        self.manager_node = Manager(self.driver, elastic_mode=elastic_mode, policies=active_policies)
        self.auditor_node = Auditor(goal=mission, constraints=["NO_DELETES"], driver=self.driver)
        
        # 3. Tool Registry
        self.tools = ToolRegistry()
        self._setup_default_tools()
        
        # 4. Checkpointing
        self.checkpointer = MemorySaver()
        
        # 5. Initial State
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
        
        # 6. Build Graph
        self.app = self._build_graph()

    def run(self, config: dict = None):
        """Execute the session until completion or halt."""
        cfg = config or {"configurable": {"thread_id": "default"}}
        for event in self.app.stream(self.state, config=cfg):
            pass # Just run it

    def _safe_path(self, path: str) -> str:
        """
        Enforces 'Path Jail' (Jailbreak protection).
        Ensures all file operations are strictly within the registered root_dirs.
        """
        # Resolve to absolute
        target = os.path.abspath(path)
        
        # Check against all allowed roots
        is_safe = any(target.startswith(rd) for rd in self.root_dirs)
        
        if not is_safe:
            # Also check relative to each root if it was a relative path input
            for rd in self.root_dirs:
                rel_target = os.path.abspath(os.path.join(rd, path))
                if rel_target.startswith(rd):
                    target = rel_target
                    is_safe = True
                    break
        
        if not is_safe:
            raise PermissionError(f"Path Traversal Blocked: Access to {path} is outside the multi-root jail.")
            
        # 3. Block sensitive files (Kernel hardcoded)
        sensitive = [".env", ".git", ".gemini", "vault_data.txt"]
        if any(s in path for s in sensitive):
            raise PermissionError(f"Security Blocked: Access to {path} is forbidden by Kernel policy.")
            
        return target

    def visualize(self):
        """Print the ASCII structure of the LangGraph state machine."""
        try:
            print("\n[Amnesic Kernel Architecture]")
            print(self.app.get_graph().draw_ascii())
            print("\n[Flow Legend]")
            print("1. Manager  (CPU) : Decides next move based on L1 Context.")
            print("2. Auditor  (Sec) : Validates move. Enforces 'One-File' rule.")
            print("3. Executor (I/O) : Performs action. Clears L1 (Forced Amnesia).")
            print("   (Loop returns to Manager with new state)\n")
        except Exception as e:
            print(f"[WARN] Could not visualize graph: {e}")

    def query(self, question: str, config: dict = None) -> str:
        """
        Ask the agent a question based on its CURRENT state (Time Travel / Hive Mind).
        This bypasses the full loop and just runs the Manager for one thought.
        """
        cfg = config or {"configurable": {"thread_id": "default"}}
        
        # Update mission temporarily for the query
        # In a real impl, we'd inject this as a user message, but here we hack the system prompt
        current_state = self.app.get_state(cfg).values
        if not current_state:
            current_state = self.state
            
        fw_state = current_state.get('framework_state')
        # Inject question into artifacts or hypothesis
        fw_state.current_hypothesis = f"QUERY: {question}"
        
        # Inject Shared Knowledge (Hive Mind) - Fix for query bypass
        if self.sidecar:
            shared_knowledge = self.sidecar.get_all_knowledge()
            for k, v in shared_knowledge.items():
                if not any(a.identifier == k for a in fw_state.artifacts):
                    fw_state.artifacts.append(Artifact(
                        identifier=k, type="config", summary=str(v), status="verified_invariant"
                    ))
        
        # Use Manager directly to get an answer
        # We need to render context manually since we aren't stepping the graph
        l1_status = f"L1 RAM CONTENT: {', '.join(self.pager.active_pages.keys())}"
        
        move = self.manager_node.decide(
            state=fw_state,
            file_map=self.env.refresh_substrate(),
            pager=self.pager,
            active_context=l1_status
        )
        return move.thought_process

    def snapshot_state(self, label: str) -> str:
        """Create a named snapshot of the current artifacts."""
        if not hasattr(self, "_snapshots"): self._snapshots = {}
        # Deep copy artifacts
        import copy
        self._snapshots[label] = copy.deepcopy(self.state['framework_state'].artifacts)
        return label

    def restore_state(self, snapshot_id: str):
        """Restore artifacts from a snapshot."""
        if hasattr(self, "_snapshots") and snapshot_id in self._snapshots:
            import copy
            self.state['framework_state'].artifacts = copy.deepcopy(self._snapshots[snapshot_id])
            self.state['framework_state'].current_hypothesis = f"RESTORED SNAPSHOT: {snapshot_id}"

    # --- Setup & Nodes ---

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
        """Removes an artifact from state. Triggers L1 wipe in strict mode."""
        self.state['framework_state'].artifacts = [a for a in self.state['framework_state'].artifacts if a.identifier != target]
        if self.sidecar: self.sidecar.delete_knowledge(target)
        
        self.state['framework_state'].last_action_feedback = f"Artifact {target} DELETED."
        
        # Amnesic Wipe
        if not self.elastic_mode:
            active_files = [p for p in self.pager.active_pages.keys() if "FILE:" in p]
            for file_id in active_files: self.pager.evict_to_l2(file_id)

    def _tool_stage_artifact(self, target: str):
        """Loads artifact content into L1 RAM."""
        found = next((a for a in self.state['framework_state'].artifacts if a.identifier == target), None)
        if found:
            self.pager.request_access(f"FILE:ARTIFACT:{target}", found.summary, priority=10)
            self.state['framework_state'].last_action_feedback = f"Artifact {target} staged into L1 RAM."
        else:
            self.state['framework_state'].last_action_feedback = f"Error: Artifact {target} not found."

    def _tool_switch_strategy(self, target: str):
        """Dynamically updates the agent's operating persona/strategy."""
        self.state['framework_state'].strategy = target
        self.state['framework_state'].last_action_feedback = f"Strategy Switched: Now acting as {target}"

    def _tool_compare_files(self, target: str):
        """
        Dual-Slot Comparator Tool.
        Target: 'file_a.py, file_b.py'
        """
        if "," not in target:
            self.state['framework_state'].last_action_feedback = "Error: compare_files requires two files separated by comma."
            return

        file_a, file_b = [f.strip() for f in target.split(",", 1)]
        
        # Load content
        content_a, content_b = "", ""
        if os.path.exists(file_a): 
            with open(file_a) as f: content_a = f.read()
        if os.path.exists(file_b):
            with open(file_b) as f: content_b = f.read()
            
        # Attempt Dual Load
        if self.comparator.load_pair(file_a, content_a, file_b, content_b):
            # Run Worker
            worker = Worker(self.driver)
            context = self.pager.render_context()
            result = worker.execute_task(
                task_description=f"Compare {file_a} and {file_b}. Synthesize a RESOLVED version that merges logic from both. Return ONLY the merged code.",
                active_context=context,
                constraints=["Focus on semantic merging.", "Do not output markdown."]
            )
            
            # Save Diff Artifact
            self.state['framework_state'].artifacts.append(Artifact(
                identifier=f"MERGED_{os.path.basename(file_a)}_{os.path.basename(file_b)}",
                type="code_file",
                summary=result.content,
                status="verified_invariant"
            ))
            self.state['framework_state'].current_hypothesis = f"Comparison complete: {result.content[:50]}..."
            
            # Strict Cleanup
            self.comparator.purge_pair()
        else:
            self.state['framework_state'].last_action_feedback = "OOM: Cannot compare files; combined size exceeds context limit."

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("manager", self._node_manager)
        workflow.add_node("auditor", self._node_auditor)
        workflow.add_node("executor", self._node_executor)

        workflow.set_entry_point("manager")
        workflow.add_edge("manager", "auditor")
        
        def router(state: AgentState):
            if state['last_audit']['auditor_verdict'] == "PASS":
                if state['manager_decision'].tool_call == "halt_and_ask":
                    return END
            return "executor"

        workflow.add_conditional_edges("auditor", router, {"executor": "executor", END: END})
        workflow.add_edge("executor", "manager")

        return workflow.compile(checkpointer=self.checkpointer)

    # --- Node Implementations ---

    def _node_manager(self, state: AgentState):
        self.pager.tick()
        current_map = self.env.refresh_substrate()
        
        # RENDER INFRASTRUCTURE TRUTH
        active_pages = [p.replace("FILE:", "") for p in self.pager.active_pages.keys() if "SYS:" not in p]
        l1_ram_status = f"L1 RAM CONTENT: {', '.join(active_pages) if active_pages else 'EMPTY'}"
        
        # Inject Shared Knowledge (Hive Mind)
        if self.sidecar:
            shared_knowledge = self.sidecar.get_all_knowledge()
            # Convert shared knowledge into transient artifacts for the Manager's view
            for k, v in shared_knowledge.items():
                if not any(a.identifier == k for a in state['framework_state'].artifacts):
                    state['framework_state'].artifacts.append(Artifact(
                        identifier=k, type="config", summary=str(v), status="verified_invariant"
                    ))

        history = state['framework_state'].decision_history
        history_lines = [f"Turn {i}: {h.get('tool_call', 'unknown')} -> {h['auditor_verdict']} ({h.get('rationale', '')})" for i, h in enumerate(history)]
        compressed_hist = compress_history(history_lines, max_turns=5)
        
        # Inject Infrastructure Truth to prevent State-Context Desync
        l1_truth = f"STAGED_FILES: {', '.join(active_pages) if active_pages else 'EMPTY'}"
        history_block = f"[CURRENT INFRASTRUCTURE STATE]\n{l1_truth}\n\n[HISTORY]\n" + (compressed_hist if compressed_hist else "")

        move = self.manager_node.decide(
            state=state['framework_state'],
            file_map=current_map,
            pager=self.pager,
            history_block=history_block,
            active_context=l1_ram_status
        )
        return {"manager_decision": move, "active_file_map": current_map, "last_node": "manager"}

    def _node_auditor(self, state: AgentState):
        move = state['manager_decision']
        
        # --- LAYER 0: PHYSICAL PRE-FLIGHT (Hardened) ---
        if move.tool_call in ["stage_context", "edit_file", "write_file"]:
            try:
                # Extract path from target (handles 'path: instruction' for edit/write)
                path = move.target.split(":", 1)[0].strip() if ":" in move.target else move.target
                self._safe_path(path)
            except PermissionError as e:
                audit = {"auditor_verdict": "REJECT", "rationale": f"PHYSICAL SECURITY VIOLATION: {str(e)}"}
                state['framework_state'].decision_history.append({
                    "turn": len(state['framework_state'].decision_history) + 1,
                    "tool_call": move.tool_call,
                    "target": move.target,
                    "move": move.model_dump(),
                    "auditor_verdict": audit["auditor_verdict"],
                    "rationale": audit["rationale"]
                })
                return {"last_audit": audit, "framework_state": state['framework_state'], "last_node": "auditor"}

        raw_map = state.get('active_file_map', [])
        valid_files = [f['path'] for f in raw_map] if raw_map else []
        active_pages = list(self.pager.active_pages.keys())
        active_content = self.pager.render_context()
        
        existing_artifacts = [a.identifier for a in state['framework_state'].artifacts]
        file_pages = [p for p in active_pages if "FILE:" in p]
        
        # Enforce Cognitive Load Shaping (Single File Constraint)
        if move.tool_call == "stage_context" and len(file_pages) > 0 and not self.elastic_mode:
             blocking_file = file_pages[0].replace("FILE:", "")
             audit = {"auditor_verdict": "REJECT", "rationale": f"L1 Violation: Memory full (Strict Mode). You MUST 'unstage_context' ({blocking_file}) before staging {move.target}."}
             state['framework_state'].last_action_feedback = f"Error: Cannot stage {move.target}. File {blocking_file} is already occupying L1. Unstage it first."
             # Return early to block execution
             state['framework_state'].decision_history.append({
                "turn": len(state['framework_state'].decision_history) + 1,
                "tool_call": move.tool_call,
                "target": move.target,
                "move": move.model_dump(),
                "auditor_verdict": audit["auditor_verdict"],
                "rationale": audit["rationale"]
             })
             return {"last_audit": audit, "framework_state": state['framework_state'], "last_node": "auditor"}

        if move.tool_call == "save_artifact" and move.target in existing_artifacts:
            audit = {"auditor_verdict": "REJECT", "rationale": f"Artifact {move.target} is already saved. Use Semantic Bridging to update."}
        elif move.tool_call == "stage_context" and len(file_pages) > 0 and not self.elastic_mode:
             blocking_file = file_pages[0].replace("FILE:", "")
             audit = {"auditor_verdict": "REJECT", "rationale": f"L1 Violation: Memory full (Strict Mode). You MUST 'unstage_context' ({blocking_file}) before staging {move.target}."}
             state['framework_state'].last_action_feedback = f"Error: Cannot stage {move.target}. File {blocking_file} is already occupying L1. Unstage it first."
        elif move.tool_call == "stage_context":
            if move.target not in valid_files:
                 audit = {"auditor_verdict": "REJECT", "rationale": f"File {move.target} does not exist on disk."}
            else:
                audit = {"auditor_verdict": "PASS", "rationale": "Staging permitted (L1 is empty)."}
        elif move.tool_call in ["save_artifact", "delete_artifact", "stage_artifact", "calculate", "verify_step", "edit_file", "write_file", "halt_and_ask", "compare_files", "switch_strategy"]:
             audit = {"auditor_verdict": "PASS", "rationale": "Internal state management tool."}
        else:
            audit = self.auditor_node.evaluate_move(
                move.tool_call, move.target, move.thought_process,
                valid_files, active_pages, state['framework_state'].decision_history,
                state['framework_state'].artifacts, active_context=active_content
            )
        
        state['framework_state'].decision_history.append({
            "turn": len(state['framework_state'].decision_history) + 1,
            "tool_call": move.tool_call,
            "target": move.target,
            "move": move.model_dump(),
            "auditor_verdict": audit["auditor_verdict"],
            "rationale": audit["rationale"]
        })
        
        return {"last_audit": audit, "framework_state": state['framework_state'], "last_node": "auditor"}

    def _node_executor(self, state: AgentState):
        move = state['manager_decision']
        audit = state['last_audit']
        
        # Sync Session with Graph Truth
        self.state['framework_state'] = state['framework_state']
        
        if audit["auditor_verdict"] == "PASS":
            try:
                self.tools.execute(move.tool_call, target=move.target)
                if move.tool_call == "save_artifact":
                    state['framework_state'].last_action_feedback = f"Artifact Saved. L1 Cache Cleared."
                else:
                    state['framework_state'].last_action_feedback = f"Successfully executed {move.tool_call}"
            except Exception as e:
                state['framework_state'].last_action_feedback = f"TOOL ERROR: {str(e)}"
                state['framework_state'].confidence_score -= 0.2
        else:
            state['framework_state'].last_action_feedback = f"Auditor REJECTED: {audit['rationale']}"
            state['framework_state'].confidence_score = max(0.0, state['framework_state'].confidence_score - 0.1)

        # Return updated state to Graph
        return {"framework_state": self.state['framework_state'], "last_node": "executor"}

    # --- Tool Implementations ---
    def _tool_stage(self, target: str):
        targets = [t.strip() for t in target.replace(',', ' ').split() if t.strip()]
        for raw_path in targets:
            try:
                # Clean path: strip quotes
                file_path = raw_path.strip("'").strip('"')
                
                # Normalize target name for L1 mapping
                l1_key = os.path.basename(file_path)
                
                safe_target = self._safe_path(file_path)
                if os.path.exists(safe_target):
                    with open(safe_target, 'r', errors='replace') as f:
                        content = f.read()
                    if not self.pager.request_access(f"FILE:{l1_key}", content, priority=8):
                        raise ValueError(f"OOM: File '{l1_key}' ({len(content)//4} tokens) exceeds L1 Capacity.")
                    
                    self.state['framework_state'].last_action_feedback = f"SUCCESS: Context '{l1_key}' loaded into L1 RAM."
                else:
                    self.state['framework_state'].last_action_feedback = f"Error: File '{file_path}' not found on disk. Did you use the full relative path?"
            except PermissionError as e:
                self.state['framework_state'].last_action_feedback = f"Security Error: {str(e)}"
            except Exception as e:
                self.state['framework_state'].last_action_feedback = f"Stage Error: {str(e)}"

    def _tool_unstage(self, target: str):
        # Clean target: strip whitespace and quotes
        clean_target = target.strip().strip("'").strip('"')
        l1_key = os.path.basename(clean_target)
        
        if f"FILE:{l1_key}" in self.pager.active_pages:
            self.pager.evict_to_l2(f"FILE:{l1_key}")
            self.state['framework_state'].last_action_feedback = f"SUCCESS: Context '{l1_key}' unstaged and memory wiped."
        else:
            # Idempotency: If not found, assume it's already gone to prevent logic loops
            self.state['framework_state'].last_action_feedback = f"NOTICE: {clean_target} was not in L1 (already unstaged)."

    def _tool_worker_task(self, target: str):
        active_context = self.pager.render_context()
        worker = Worker(self.driver)
        result = worker.execute_task(f"Extract {target}", active_context, ["Output ONLY the raw value."])
        
        # Self-Correction: Check if artifact exists and overwrite
        existing_idx = next((i for i, a in enumerate(self.state['framework_state'].artifacts) if a.identifier == target), None)
        new_artifact = Artifact(identifier=target, type="text_content", summary=result.content, status="verified_invariant")
        
        if existing_idx is not None:
            self.state['framework_state'].artifacts[existing_idx] = new_artifact
            self.state['framework_state'].last_action_feedback = f"Artifact {target} UPDATED/CORRECTED."
        else:
            self.state['framework_state'].artifacts.append(new_artifact)
            self.state['framework_state'].last_action_feedback = f"Artifact Saved. L1 Cache Cleared."

        if self.sidecar: self.sidecar.ingest_knowledge(target, result.content)
        if "Initial Assessment" in self.state['framework_state'].current_hypothesis:
            self.state['framework_state'].current_hypothesis = f"Found {target}={result.content}"
        else:
            self.state['framework_state'].current_hypothesis += f", {target}={result.content}"
        
        # Auto-Evict only in Strict Mode
        if not self.elastic_mode:
            active_files = [p for p in self.pager.active_pages.keys() if "FILE:" in p]
            for file_id in active_files: self.pager.evict_to_l2(file_id)

    def _tool_write_file(self, target: str):
        """Writes a new file. Target: 'path: content' OR 'path: ARTIFACT:id'"""
        if ":" not in target:
            self.state['framework_state'].last_action_feedback = "Error: write_file requires 'path: content'."
            return

        path, content = target.split(":", 1)
        path = path.strip()
        content = content.strip()
        
        safe_path = self._safe_path(path)

        # Artifact Reference Expansion
        if content.startswith("ARTIFACT:"):
            art_id = content.replace("ARTIFACT:", "").strip()
            # Find artifact
            found = next((a for a in self.state['framework_state'].artifacts if a.identifier == art_id), None)
            if found:
                content = found.summary
            else:
                self.state['framework_state'].last_action_feedback = f"Error: Artifact {art_id} not found."
                return

        try:
            with open(safe_path, "w") as f: f.write(content)
            self.state['framework_state'].last_action_feedback = f"Successfully wrote {path}."
        except Exception as e:
            self.state['framework_state'].last_action_feedback = f"Write Error: {e}"

    def _tool_edit(self, target: str):
        """Performs surgical code edits. Target format: 'filepath: instruction'"""
        if ":" in target:
            file_path, instruction = target.split(":", 1)
            file_path = file_path.strip()
            instruction = instruction.strip()
        else:
            file_path = target
            instruction = "Fix the issue found in the file."

        safe_path = self._safe_path(file_path)
        active_context = self.pager.render_context()
        worker = Worker(self.driver)
        
        result = worker.perform_edit(
            target_file=file_path,
            instructions=instruction,
            active_context=active_context,
            constraints=["Preserve indentation.", "Output only the code snippet."]
        )
        
        if os.path.exists(safe_path):
            with open(safe_path, 'r') as f: content = f.read()
            if result.original_snippet in content:
                new_content = content.replace(result.original_snippet, result.new_snippet)
                with open(safe_path, 'w') as f: f.write(new_content)
                self.state['framework_state'].last_action_feedback = f"Successfully edited {file_path}."
                self.state['framework_state'].artifacts.append(Artifact(
                    identifier=f"diff_{os.path.basename(file_path)}",
                    type="code_file",
                    summary=f"Changed '{result.original_snippet}' to '{result.new_snippet}'",
                    status="committed"
                ))
            else:
                self.state['framework_state'].last_action_feedback = f"Edit Failed: Original snippet not found in {file_path}."
        else:
            self.state['framework_state'].last_action_feedback = f"Edit Failed: File {file_path} not found."

    def _tool_verify_step(self, target: str):
        arts = self.state['framework_state'].artifacts
        summary_text = " ".join([a.summary for a in arts]) + f" {target}"
        
        # 1. Math Verification
        operator = None
        if "MULTIPLY" in summary_text.upper(): operator = "MULTIPLY"
        elif "SUBTRACT" in summary_text.upper(): operator = "SUBTRACT"
        elif "DIVIDE" in summary_text.upper(): operator = "DIVIDE"
        elif "ADD" in summary_text.upper(): operator = "ADD"
        
        result_str = ""
        
        if operator:
            import re
            nums = [int(n) for n in re.findall(r'\d+', summary_text)]
            result = 0
            if nums:
                if operator == "ADD": result = sum(nums)
                elif operator == "MULTIPLY": 
                    result = 1
                    for n in nums: result *= n
                elif operator == "SUBTRACT": result = nums[0] - sum(nums[1:]) if len(nums) > 1 else nums[0]
                elif operator == "DIVIDE": 
                    result = nums[0]
                    for n in nums[1:]:
                        if n != 0: result /= n
            result_str = f"Final Calculation ({operator}): {result}"
            # Only save TOTAL if math was actually performed
            self.state['framework_state'].artifacts.append(Artifact(identifier="TOTAL", type="result", summary=result_str, status="committed"))
        
        # 2. Semantic/Text Verification (Fallback)
        else:
            active_content = self.pager.render_context()
            
            # Check if target string is in content OR if target file is loaded
            is_loaded = any(target in pid for pid in self.pager.active_pages.keys())
            is_in_text = target in active_content
            
            if is_in_text:
                result_str = f"Verification PASSED: '{target}' found in active context."
            elif is_loaded:
                result_str = f"Verification PASSED: File '{target}' is currently loaded."
            else:
                result_str = f"Verification NOTE: '{target}' not found in active context."
            
            # Save generic verification artifact
            self.state['framework_state'].artifacts.append(Artifact(identifier="VERIFICATION", type="result", summary=result_str, status="committed"))

        self.state['framework_state'].current_hypothesis = result_str

    def _tool_calculate(self, target: str):
        arts = self.state['framework_state'].artifacts
        summary_text = " ".join([a.summary for a in arts]) + f" {target}"
        
        operator = None
        # Prioritize explicit symbols in target
        if "*" in target: operator = "MULTIPLY"
        elif "/" in target: operator = "DIVIDE"
        elif "+" in target: operator = "ADD"
        elif "-" in target: operator = "SUBTRACT"
        # Fallback to word detection
        elif "MULTIPLY" in summary_text.upper(): operator = "MULTIPLY"
        elif "SUBTRACT" in summary_text.upper(): operator = "SUBTRACT"
        elif "DIVIDE" in summary_text.upper(): operator = "DIVIDE"
        elif "ADD" in summary_text.upper(): operator = "ADD"

        if operator:
            import re
            nums = [int(n) for n in re.findall(r'\d+', summary_text)]
            result = 0
            if nums:
                if operator == "ADD": result = sum(nums)
                elif operator == "MULTIPLY": 
                    result = 1
                    for n in nums: result *= n
                elif operator == "SUBTRACT": result = nums[0] - sum(nums[1:]) if len(nums) > 1 else nums[0]
                elif operator == "DIVIDE": 
                    result = nums[0]
                    for n in nums[1:]:
                        if n != 0: result /= n
            result_str = f"Final Calculation ({operator}): {result}"
            self.state['framework_state'].artifacts.append(Artifact(identifier="TOTAL", type="result", summary=result_str, status="committed"))
            self.state['framework_state'].current_hypothesis = result_str
        else:
            self._tool_verify_step(target)

    
        