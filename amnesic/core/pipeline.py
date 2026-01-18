from typing import List, Dict, Callable, Optional, Union, Any
import re
from rich.console import Console
from rich.panel import Panel
from .session import AmnesicSession
from .sidecar import SharedSidecar

class PipelineStep:
    def __init__(self, name: str, mission: str, profile: str = "STRICT_AUDIT", forbidden_tools: List[str] = None):
        self.name = name
        self.mission = mission
        self.profile = profile
        self.forbidden_tools = forbidden_tools or []

class MapStep(PipelineStep):
    def __init__(self, name: str, input_artifact: str, mission_template: str, profile: str = "STRICT_AUDIT", forbidden_tools: List[str] = None):
        super().__init__(name, mission_template, profile, forbidden_tools)
        self.input_artifact = input_artifact

class AmnesicPipeline:
    """
    Meta-Controller for stringing together multiple AmnesicSessions.
    Enables "Scout -> Map -> Reduce" workflows with shared long-term memory.
    """
    def __init__(self, default_recursion_limit: int = 50):
        self.sidecar = SharedSidecar()
        self.steps = []
        self.console = Console()
        self.default_recursion_limit = default_recursion_limit

    def add_step(self, name: str, mission: str, profile: str = "STRICT_AUDIT", forbidden_tools: List[str] = None):
        """Add a single linear task."""
        self.steps.append(PipelineStep(name, mission, profile, forbidden_tools))
        return self

    def add_map_step(self, name: str, input_artifact: str, mission_template: str, profile: str = "STRICT_AUDIT", forbidden_tools: List[str] = None):
        """
        Executes a mission for EACH item in the comma/newline separated input_artifact.
        Use {item} in mission_template to inject the value.
        
        Example: 
            pipeline.add_map_step("workers", "FILE_LIST", "Refactor {item}")
        """
        self.steps.append(MapStep(name, input_artifact, mission_template, profile, forbidden_tools))
        return self

    def run(self):
        self.console.print(Panel("[bold green]Starting Amnesic Pipeline[/bold green]", border_style="green"))
        
        for step in self.steps:
            self.console.print(f"\n[bold cyan]>>> Running Step: {step.name}[/bold cyan]")
            
            try:
                if isinstance(step, MapStep):
                    self._run_map_step(step)
                else:
                    self._run_single_step(step)
            except Exception as e:
                self.console.print(f"[bold red]Pipeline Error in step '{step.name}': {e}[/bold red]")
                # We typically want to stop on error, or maybe continue? 
                # For now, let's stop to be safe.
                break
                
        self.console.print(Panel("[bold green]Pipeline Complete[/bold green]", border_style="green"))

    def _run_single_step(self, step: PipelineStep):
        # Create session sharing the GLOBAL sidecar
        session = AmnesicSession(
            mission=step.mission,
            audit_profile=step.profile,
            sidecar=self.sidecar,
            recursion_limit=self.default_recursion_limit,
            forbidden_tools=step.forbidden_tools
        )
        session.run()
        # No need to manually extract artifacts, they are already in the Sidecar

    def _run_map_step(self, step: MapStep):
        # 1. Retrieve the input artifact from Sidecar
        # The sidecar stores knowlege as a dict.
        # Note: shared_sidecar.get_all_knowledge returns {key: content} or similar depending on internals.
        knowledge = self.sidecar.get_all_knowledge()
        
        # We look for the artifact key. Handle case sensitivity?
        # Let's assume strict keys for now.
        raw_data = knowledge.get(step.input_artifact, "")
        
        # Fallback: Check if it's stored as a dict with 'content' (legacy sidecar structure)
        if isinstance(raw_data, dict) and 'content' in raw_data:
            raw_data = raw_data['content']
            
        if not raw_data:
            self.console.print(f"[bold red]SKIPPING MAP STEP: Artifact '{step.input_artifact}' not found in Sidecar.[/bold red]")
            self.console.print(f"[dim]Available keys: {list(knowledge.keys())}[/dim]")
            return

        # 2. Parse items (Comma or Newline)
        # Robust split that handles [item1, item2] brackets too
        cleaned_data = str(raw_data).replace("[", "").replace("]", "").replace('"', "").replace("'", "")
        items = [i.strip() for i in re.split(r'[,\n]', cleaned_data) if i.strip()]
        
        self.console.print(f"[dim]Found {len(items)} items to process from {step.input_artifact}[/dim]")
        
        # 3. Run sub-sessions
        for i, item in enumerate(items):
            self.console.print(f"   [yellow]Worker {i+1}/{len(items)}: Processing '{item}'[/yellow]")
            try:
                mission = step.mission.format(item=item)
            except KeyError:
                # If template fails (e.g. user didn't put {item}), just run as is
                mission = f"{step.mission} (Target: {item})"
            
            session = AmnesicSession(
                mission=mission,
                audit_profile=step.profile,
                sidecar=self.sidecar,
                recursion_limit=self.default_recursion_limit,
                forbidden_tools=step.forbidden_tools
            )
            session.run()
