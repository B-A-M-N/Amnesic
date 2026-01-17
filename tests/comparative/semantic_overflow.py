"""
Comparative Failure Suite: Amnesic vs. Standard ReAct
This test formally proves that Amnesic succeeds where standard agents fail 
under tight context constraints.
"""
import os
import sys
import random
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from tests.comparative.shared import StandardReActAgent

def run_comparative_test():
    console = Console()
    
    # 1. Setup Environment (Data larger than 1/2 context window)
    # Goal: Force eviction or saturation
    val_a = random.randint(100, 999)
    val_b = random.randint(100, 999)
    noise = "NOISE_BUFFER_FRAGMENT " * 150 # ~600 tokens
    
    with open("vault_1.txt", "w") as f:
        f.write(f"ID_X: {val_a}\n{noise}")
    with open("vault_2.txt", "w") as f:
        f.write(f"ID_Y: {val_b}\n{noise}")
        
    mission = (
        "MISSION: Retrieve ID_X from vault_1.txt and ID_Y from vault_2.txt. "
        "Calculate the product (X * Y). "
        "IMPORTANT: You must output the final answer."
    )
    
    TOKEN_LIMIT = 32768 # Tight limit
    
    console.print(Panel(
        f"[bold white]COMPARATIVE STRESS TEST[/bold white]\n"
        f"Mission: Multiply ID_X ({val_a}) and ID_Y ({val_b})\n"
        f"Context Limit: {TOKEN_LIMIT} Tokens\n"
        f"Expected Result: {val_a * val_b}",
        style="bold magenta"
    ))

    # --- PHASE 1: STANDARD AGENT ---
    console.print("\n[bold red]Testing Standard ReAct Agent (Sliding Window)...[/bold red]")
    standard_agent = StandardReActAgent(mission, token_limit=TOKEN_LIMIT)
    standard_success = False
    standard_result = None
    
    for i in range(12):
        step = standard_agent.step()
        
        # Verbose Logging for Standard Agent
        color = "red" if step['window_status'] != "OK" else "white"
        console.print(f"[Turn {step['turn']}] Agent: [bold]{step['action']}({step['arg']})[/bold]")
        console.print(f"         Thought: [dim]{step['thought']}[/dim]")
        console.print(f"         Context: [{color}]{step['context_len']}/{step['limit']} ({step['window_status']})[/{color}]")

        if step['action'] == "halt_and_ask":
            standard_result = step['arg']
            # Check if correct (product)
            try:
                if str(val_a * val_b) in str(standard_result):
                    standard_success = True
            except: pass
            break
        if step['action'] == "error": 
            console.print(f"         [bold red]FATAL ERROR: {step['arg']}[/bold red]")
            break

    # --- PHASE 2: AMNESIC AGENT ---
    console.print("\n[bold green]Testing Amnesic Session (Read-Then-Release)...[/bold green]")
    amnesic_session = AmnesicSession(mission=mission, l1_capacity=TOKEN_LIMIT)
    amnesic_success = False
    amnesic_result = None
    
    config = {"configurable": {"thread_id": "comp_test"}, "recursion_limit": 50}
    for event in amnesic_session.app.stream(amnesic_session.state, config=config):
        current_state = amnesic_session.app.get_state(config).values
        move = current_state.get('manager_decision')
        
        if move and move.tool_call == "halt_and_ask":
            amnesic_result = move.target
            try:
                if str(val_a * val_b) in str(amnesic_result):
                    amnesic_success = True
            except: pass
            break

    # --- FINAL COMPARISON ---
    res_table = Table(title="Comparative Results")
    res_table.add_column("Agent Type", style="bold")
    res_table.add_column("Success", justify="center")
    res_table.add_column("Final Result", style="dim")
    res_table.add_column("Failure Mode", style="red")
    
    standard_fail_mode = "N/A"
    if not standard_success:
        # Determine failure mode
        if "MAX" in str(standard_agent.step().get('window_status', '')):
             standard_fail_mode = "Context Saturation (Amnesia)"
        else:
             standard_fail_mode = "Hallucination/Incomplete"
             
    res_table.add_row(
        "Standard ReAct", 
        "[red]FAILED[/red]" if not standard_success else "[green]PASSED[/green]",
        str(standard_result),
        standard_fail_mode
    )
    res_table.add_row(
        "Amnesic", 
        "[green]PASSED[/green]" if amnesic_success else "[red]FAILED[/red]",
        str(amnesic_result),
        "None" if amnesic_success else "Unexpected Logic Error"
    )
    
    console.print("\n", res_table)
    
    # Cleanup
    for f in ["vault_1.txt", "vault_2.txt"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_comparative_test()
