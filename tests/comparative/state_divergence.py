"""
Comparative Proof: Incoherent Collaboration vs. Synchronized Sidecar
Proves that disconnected agents diverge, while Amnesic agents 
maintain global coherence via L3 synchronization.
"""
import os
import sys
from rich.console import Console
from rich.panel import Panel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from amnesic.core.sidecar import SharedSidecar
from amnesic.presets.code_agent import Artifact
from tests.comparative.shared import StandardReActAgent

def run_divergence_test():
    console = Console()
    
    shared_sidecar = SharedSidecar()
    mission = "MISSION: Ensure 'SYSTEM_STATUS' is consistent."
    
    console.print(Panel(
        "[bold white]COMPARATIVE PROOF: Incoherent Collaboration[/bold white]\n"
        "Failure Mode: [bold red]STATE SPLIT (Divergence)[/bold red]\n"
        "Scenario: Agent A updates status to 'READY'. Agent B must know without being told.",
        style="bold cyan"
    ))

    # --- PHASE 1: STANDARD AGENT ---
    # (Already proven in state_sync.py, but we'll formalize the 'Divergence' here)
    console.print("\n[bold red]Testing Standard Agents (Disconnected)...[/bold red]")
    self_a = StandardReActAgent(mission)
    self_b = StandardReActAgent(mission)
    
    self_a.history.append({"role": "assistant", "content": "I am setting SYSTEM_STATUS to 'ONLINE'."})
    # self_b has NO knowledge of this. 
    res_b = self_b.driver.generate_raw("What is the SYSTEM_STATUS?", "Answer based on your history.")
    
    console.print(f"Agent B Knowledge: [red]{res_b[:50]}...[/red]")
    if "ONLINE" not in res_b:
        console.print("[bold red]!! DIVERGENCE: Agent B is operating in a state vacuum.[/bold red]")

    # --- PHASE 2: AMNESIC AGENTS ---
    console.print("\n[bold green]Testing Amnesic Agents (Synchronized Sidecar)...[/bold green]")
    
    # Agent A (Session 1) - Set State
    session_a = AmnesicSession(mission=mission, sidecar=shared_sidecar)
    session_a._tool_worker_task("SYSTEM_STATUS: ONLINE")
    console.print("Agent A: Committed 'SYSTEM_STATUS: ONLINE' to L3.")

    # Agent B (Session 2) - Pull State
    session_b = AmnesicSession(mission="Check Status", sidecar=shared_sidecar)
    # The Sidecar is automatically read during query or turn 0
    status_in_b = session_b.query("What is the SYSTEM_STATUS?")
    
    console.print(f"Agent B Knowledge: [bold green]{status_in_b}[/bold green]")
    if "ONLINE" in status_in_b:
        console.print("\n[bold green]✔ SUCCESS: Agent B synchronized via L3. Zero divergence.[/bold green]")

if __name__ == "__main__":
    run_divergence_test()
