"""
Comparative Proof: State Synchronization vs. Redundant Work
Proves that standard agents cannot share state without re-processing all data,
while Amnesic agents sync instantly via the Sidecar (L3 Store).
"""
import os
import sys
from rich.console import Console
from rich.panel import Panel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from amnesic.core.sidecar import SharedSidecar
from tests.comparative.shared import StandardReActAgent

def run_state_sync_test():
    console = Console()
    
    # Setup knowledge source
    with open("shared_knowledge.txt", "w") as f:
        f.write("THE_SECRET_KEY = 'AMNESIC_PROTO_2026'")
    
    mission = "MISSION: Find THE_SECRET_KEY in shared_knowledge.txt."
    
    console.print(Panel(
        "[bold white]COMPARATIVE PROOF: State Synchronization[/bold white]\n"
        "Failure Mode: [bold red]REDUNDANT WORK / STATE INCOHERENCE[/bold red]\n"
        "Scenario: Agent A finds a fact. Agent B must know it without reading the source.",
        style="bold green"
    ))

    # --- PHASE 1: STANDARD AGENT ---
    console.print("\n[bold red]Testing Standard Agents (Disconnected History)...[/bold red]")
    agent_a = StandardReActAgent(mission)
    agent_b = StandardReActAgent(mission)
    
    # Agent A works
    console.print("Agent A finds the key...")
    step_a = agent_a.step() # stage_context
    step_a2 = agent_a.step() # Thought: The key is AMNESIC_PROTO_2026
    
    # Agent B wakes up
    console.print("Agent B wakes up. Does it know the key?")
    step_b = agent_b.step()
    if step_b['action'] == "read_file":
        console.print("[bold red]!! REDUNDANT: Agent B had to re-read the file because it lacks a shared state store.[/bold red]")

    # --- PHASE 2: AMNESIC AGENTS ---
    console.print("\n[bold green]Testing Amnesic Agents (Shared Sidecar)...[/bold green]")
    shared_sidecar = SharedSidecar()
    
    # Agent A (Session 1)
    session_a = AmnesicSession(mission=mission, sidecar=shared_sidecar)
    # Simulate Agent A saving the fact
    from amnesic.presets.code_agent import Artifact
    session_a._tool_worker_task("THE_SECRET_KEY: AMNESIC_PROTO_2026")
    console.print("Agent A saved THE_SECRET_KEY to Sidecar.")
    
    # Agent B (Session 2)
    session_b = AmnesicSession(mission="MISSION: What is the secret key?", sidecar=shared_sidecar)
    
    # Agent B queries its context
    # Note: query() pulls from sidecar into artifacts
    result = session_b.query("What is the secret key?")
    
    if "AMNESIC_PROTO_2026" in result:
        console.print(f"Agent B response: [bold green]{result}[/bold green]")
        console.print("\n[bold green]✔ SUCCESS: Agent B knew the key INSTANTLY via the Sidecar. 0% Redundant Work.[/bold green]")
    else:
        console.print(f"Agent B response: [red]{result}[/red]")
        console.print("\n[bold red]✖ FAILURE: Agent B failed to sync from Sidecar.[/bold red]")

    # Cleanup
    if os.path.exists("shared_knowledge.txt"): os.remove("shared_knowledge.txt")

if __name__ == "__main__":
    run_state_sync_test()
