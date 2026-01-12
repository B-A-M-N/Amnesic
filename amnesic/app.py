import logging
import os
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.logging import RichHandler

from .drivers.factory import get_driver
from .tools.ast_mapper import StructuralMapper
from .tools.hybrid_search import HybridSearcher
from .core.dynamic_pager import DynamicPager
from .decision.manager import Manager
from .decision.auditor import Auditor
from .decision.worker import Worker
from .core.tool_registry import ToolRegistry
from .presets.code_agent import FrameworkState, Artifact
from .core.memory import compress_history

# Setup Logging
logging.basicConfig(
    level="ERROR",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

class FrameworkApp:
    def __init__(self, mission: str, root_dir: str = "./", model: str = "qwen2.5-coder:7b", provider: str = "ollama", use_hybrid: bool = False):
        self.mission = mission
        self.root_dir = root_dir
        self.console = Console()
        self.driver = get_driver(provider, model)
        
        # 1. Scaffolding: MMU & Search
        if use_hybrid:
            self.searcher = HybridSearcher(root_dir, self.driver)
            self.mapper = self.searcher.mapper
        else:
            self.searcher = None
            self.mapper = StructuralMapper(root_dir=root_dir)
            
        v_store = self.searcher.vector_store if self.searcher else None
        self.pager = DynamicPager(capacity_tokens=4000, vector_store=v_store)
        self.pager.pin_page("SYS:MISSION", f"MISSION: {mission}")

        # 2. Nodes
        self.manager = Manager(self.driver)
        self.auditor = Auditor(goal=mission, constraints=["NO_DELETES"], driver=self.driver)
        self.worker = Worker(self.driver)

        # 3. Tool Registry (The "Framework" part)
        self.tools = ToolRegistry()
        self._setup_default_tools()
        
        # 4. State (Generic)
        self.state = FrameworkState(
            task_intent=mission,
            current_hypothesis="Initial Assessment",
            hard_constraints=["Local Only"],
            plan=[],
            artifacts=[],
            confidence_score=0.5,
            unknowns=["Context Structure"]
        )

    def _setup_default_tools(self):
        """Registers the core Amnesic tools."""
        self.tools.register_tool("stage_context", self._tool_stage)
        self.tools.register_tool("unstage_context", self._tool_unstage)
        self.tools.register_tool("write_artifact", self._tool_worker_task)
        self.tools.register_tool("edit_file", self._tool_edit)
        self.tools.register_tool("verify_step", lambda **kwargs: self.console.print("[green]Step Verified.[/green]"))
        self.tools.register_tool("halt_and_ask", lambda target, **kwargs: self.console.print(f"[bold red]HALT:[/bold red] {target}"))

    def _execute_move(self, move):
        """Generic execution via the Tool Registry."""
        try:
            # All tools receive 'target' and optional 'context'
            self.tools.execute(move.tool_call, target=move.target)
        except Exception as e:
            self.console.print(f"[red]Execution Error:[/red] {e}")

    def _tool_stage(self, target: str):
        # Allow multiple files separated by spaces or commas
        targets = [t.strip() for t in target.replace(',', ' ').split() if t.strip()]
        
        for file_path in targets:
            self.console.print(f"📥 Staging {file_path}...")
            if not os.path.exists(file_path):
                self.console.print(f"[red]Error: File {file_path} not found.[/red]")
                continue
                
            with open(file_path, 'r', errors='replace') as f:
                content = f.read()
            self.pager.request_access(f"FILE:{file_path}", content, priority=8)

    def _tool_unstage(self, target: str):
        if f"FILE:{target}" in self.pager.active_pages:
            self.pager.evict_to_l2(f"FILE:{target}")
            self.console.print(f"📤 Unstaged {target}")

    def _tool_worker_task(self, target: str):
        """Delegates heavy lifting to the Worker, but ensures state update."""
        # Fast-track for simple value extraction (if target is short/simple)
        self.console.print(f"📝 Writing Artifact: {target}")
        
        # FORCE the value into the state artifacts list immediately
        # This prevents the 'Invisible Artifact' problem
        new_artifact = Artifact(
            identifier=target.split(':')[0].strip(), # Use first part as ID
            type="text_content",
            summary=f"Extracted: {target}",
            status="staged"
        )
        self.state.artifacts.append(new_artifact)
        
        # Also clean up unknowns if this matches
        self.state.unknowns = [u for u in self.state.unknowns if target not in u]
        
        self.console.print(Panel(f"Saved to State: {new_artifact.summary}", title="Artifact Committed", style="green"))

    def _tool_edit(self, target: str):
        """
        Delegates a surgical edit to the Worker.
        Target format: "path/to/file.py <Instructions>"
        """
        parts = target.split(' ', 1)
        if len(parts) < 2:
            self.console.print("[red]Error: edit_file requires 'filepath instructions'[/red]")
            return
            
        file_path, instructions = parts[0], parts[1]
        
        # Ensure file is in context
        if f"FILE:{file_path}" not in self.pager.active_pages:
            self.console.print(f"[yellow]Auto-staging {file_path} for edit...[/yellow]")
            self._tool_stage(file_path)
            
        active_context = self.pager.render_context()
        
        with Status(f"Worker is editing {file_path}...", spinner="dots"):
            edit = self.worker.perform_edit(
                target_file=file_path,
                instructions=instructions,
                active_context=active_context,
                constraints=self.state.hard_constraints
            )
            
            # Apply the edit
            try:
                # We need the real content from disk or pager to apply the replace
                # We prefer the one in Pager as it might have unsaved edits? 
                # No, Amnesic writes to Pager first usually, but let's assume disk is truth for now 
                # or read from Pager if we want to chain edits in memory.
                # For this prototype, we read from disk.
                with open(file_path, 'r') as f:
                    content = f.read()
                
                if edit.original_snippet not in content:
                    self.console.print(f"[red]Edit Failed: Original snippet not found in {file_path}[/red]")
                    self.console.print(Panel(edit.original_snippet, title="Expected Snippet"))
                    return

                new_content = content.replace(edit.original_snippet, edit.new_snippet, 1)
                
                # Write back (simulating a 'save')
                # In a real agent we might want to just update the Pager first?
                # But 'write_artifact' implies writing.
                with open(file_path, 'w') as f:
                    f.write(new_content)
                    
                # Update Pager
                self.pager.request_access(f"FILE:{file_path}", new_content, priority=9)
                
                self.console.print(Panel(f"Changed:\n{edit.original_snippet}\nTo:\n{edit.new_snippet}", title=f"Edited: {file_path}", style="green"))

            except Exception as e:
                self.console.print(f"[red]Edit Apply Error:[/red] {e}")

    def run(self, max_turns: int = 15):
        self.console.print(Panel(f"[bold green]AMNESIC FRAMEWORK[/bold green]\nMission: {self.mission}", expand=False))
        
        turn = 0
        while turn < max_turns:
            turn += 1
            self.console.print(f"\n[bold white on blue] TURN {turn}/{max_turns} [/bold white on blue]")
            
            # MMU Stats
            stats = self.pager.get_stats()
            self.console.print(f"[dim]L1 Usage: {stats['l1_used']}/{stats['l1_capacity']} tokens | Pages: {stats['pages_active']} Active, {stats['pages_swapped']} Swapped[/dim]")

            # Generic map - use searcher if available, else fallback to mapper
            if self.searcher:
                if not self.searcher.is_indexed:
                     with Status("Indexing Environment...", spinner="dots"):
                         self.searcher.index()
                current_map = self.searcher.code_map
            else:
                current_map = self.mapper.scan_repository()
            
            # PHASE 2: MANAGEMENT
            with Status("Manager is deliberating...", spinner="dots"):
                try:
                    # Construct History
                    # Safely get tool_call even if structure varies
                    def get_tool_call(h):
                        if 'tool_call' in h: return h['tool_call']
                        return h.get('move', {}).get('tool_call', 'unknown')

                    history_lines = [f"Turn {i}: {get_tool_call(h)} -> {h['auditor_verdict']}" for i, h in enumerate(self.state.decision_history)]
                    compressed_hist = compress_history(history_lines, max_turns=5)
                    history_block = "[HISTORY]\n" + compressed_hist if compressed_hist else ""

                    move = self.manager.decide(self.state, current_map, self.pager, history_block=history_block)
                except Exception as e:
                    self.console.print(f"[red]Manager Error:[/red] {e}")
                    break
            
            self.console.print(Panel(
                f"Thought: {move.thought_process}\nTool: {move.tool_call} -> {move.target}",
                title="Manager Proposal", style="cyan"
            ))

            # Update State
            if hasattr(move, 'update_hypothesis') and move.update_hypothesis:
                self.state.current_hypothesis = move.update_hypothesis
            if hasattr(move, 'new_unknowns') and move.new_unknowns:
                self.state.unknowns.extend(move.new_unknowns)

            # PHASE 3: AUDITING
            with Status("Auditor is verifying...", spinner="dots"):
                # Extract valid files from map
                valid_files = [f['path'] for f in current_map] if current_map else []
                active_pages = list(self.pager.active_pages.keys())
                audit = self.auditor.evaluate_move(
                    move.tool_call, 
                    move.target, 
                    move.thought_process, 
                    valid_files, 
                    active_pages, 
                    self.state.decision_history,
                    self.state.artifacts
                )
            
            # Record in history
            self.state.decision_history.append({
                "turn": turn,
                "tool_call": move.tool_call,
                "target": move.target,
                "move": move.model_dump(),
                "auditor_verdict": audit["auditor_verdict"],
                "rationale": audit["rationale"],
                "confidence_score": audit.get("confidence_score", 1.0)
            })

            if audit["auditor_verdict"] != "PASS":
                self.console.print(f"[bold red]⛔ BLOCKED:[/bold red] {audit['rationale']}")
                self.state.confidence_score = max(0.0, self.state.confidence_score - 0.1)
                self.state.last_action_feedback = f"REJECTED: {audit['rationale']}"
                continue

            self.console.print(f"[bold green]✅ APPROVED:[/bold green] {audit['rationale']}")
            self.state.last_action_feedback = None # Clear feedback on success

            # PHASE 4: EXECUTION
            self._execute_move(move)

            # PHASE 5: HYGIENE (Auto-Unstage)
            # "The Amnesic Protocol": If we just saved an artifact, we MUST clear the cache.
            # This prevents the "Visual Trigger" loop.
            if move.tool_call == "write_artifact":
                # Find any file in L1 that isn't pinned (System Prompt is pinned usually, but here we check active_pages)
                # In this specific test, we know it's island_a.txt or island_b.txt
                # We aggressively unstage ALL non-system files to force a state refresh.
                active_files = [p for p in self.pager.active_pages.keys() if "SYS:" not in p]
                
                if active_files:
                    self.console.print(f"[bold yellow]🧹 HYGIENE: Auto-Unstaging {len(active_files)} files to break loop.[/bold yellow]")
                    for page_id in active_files:
                        self.pager.evict_to_l2(page_id)
                        self.console.print(f"   - Evicted {page_id}")

            self.state.confidence_score = max(0.0, self.state.confidence_score - 0.05)
            
        self.console.print("[bold]System Halt.[/bold]")