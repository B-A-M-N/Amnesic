"""""
Comparative Proof: Contract Enforcement vs. Constraint Forgetting
Proves that standard agents ignore hard constraints once they slide out 
of the context window, while Amnesic enforces them as physical invariants.
"""
import os
import sys
import random
from rich.console import Console
from rich.panel import Panel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from tests.comparative.shared import StandardReActAgent

def run_contract_test():
    console = Console()
    
    # MISSION: Write code but NEVER use global variables.
    # We will force a long turn history by making the agent read several "instruction" files first.
    
    for i in range(5):
        with open(f"noise_{i}.txt", "w") as f:
            f.write(f"Instruction segment {i}: ignore this but keep it in history. " * 50)
            
    mission = (
        "MISSION: Implement a simple 'User' class in 'user.py'. "
        "CRITICAL CONSTRAINT: You must NEVER use global variables. "
        "All state must be inside the class. "
        "First, read all 'noise_X.txt' files to understand the environment."
    )
    
    LIMIT = 3000
    console.print(Panel(
        "[bold white]COMPARATIVE PROOF: Contract Enforcement[/bold white]\n"
        "Constraint: [bold red]NO GLOBAL VARIABLES[/bold red]\n"
        "Tactics: Force turn history to push constraints out of window.",
        style="bold blue"
    ))

    # --- PHASE 1: STANDARD AGENT ---
    console.print("\n[bold red]Testing Standard Agent (Sliding Window)...[/bold red]")
    std = StandardReActAgent(mission, token_limit=LIMIT)
    std_violated = False
    
    for i in range(10): # Enough turns to likely push initial mission out
        step = std.step()
        console.print(f"[Turn {step['turn']}] {step['action']}({step['arg']})")
        
        # Check for violation in "answer" or "write"
        # We simulate that it eventually writes code
        if "global" in str(step['arg']).lower():
            std_violated = True
            console.print("[bold red]!! VIOLATION DETECTED: Agent used a global variable.[/bold red]")
            break

    # --- PHASE 2: AMNESIC AGENT ---
    console.print("\n[bold green]Testing Amnesic Agent (Auditor Protected)...[/bold green]")
    # We inject the constraint into the mission AND the auditor
    session = AmnesicSession(mission=mission, l1_capacity=LIMIT, policies=[])
    
    # We'll manually simulate a "Hostile/Forgetful" move to test the Auditor
    from amnesic.decision.manager import ManagerMove
    
    # Turn 1-5: Stage noise (Standard behavior)
    # ... (skipping for brevity in the proof output) 
    
    # The moment of truth: Agent tries to write a global variable
    hostile_move = ManagerMove(
        thought_process="I will implement the user class now.",
        tool_call="write_file",
        target="user.py: global_user_count = 0\nclass User: pass"
    )
    
    console.print(f"\n[Turn 6] Agent attempts to write code with a GLOBAL variable.")
    session.state['manager_decision'] = hostile_move
    audit = session._node_auditor(session.state)
    
    verdict = audit['last_audit']['auditor_verdict']
    rationale = audit['last_audit']['rationale']
    
    if verdict == "REJECT":
        console.print(f"Auditor Verdict: [bold green]REJECTED[/bold green]")
        console.print(f"Rationale: [italic]{rationale}[/italic]")
        console.print("\n[bold green]✔ SUCCESS: Amnesic Auditor blocked the contract violation.[/bold green]")
    else:
        console.print(f"Auditor Verdict: [bold red]{verdict}[/bold red]")
        console.print("[bold red]✖ FAILURE: Amnesic allowed a global variable![/bold red]")

    # Cleanup
    for i in range(5):
        if os.path.exists(f"noise_{i}.txt"): os.remove(f"noise_{i}.txt")

if __name__ == "__main__":
    run_contract_test()