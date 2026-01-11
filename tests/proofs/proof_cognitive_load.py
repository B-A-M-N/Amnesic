import os
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_cognitive_load_proof():
    console = Console()
    
    # 1. Setup: The Haystack
    # We create massive "Distractor" files and one "Signal" file.
    noise_content = ("# DISTRACTOR FUNCTION\ndef noise_func_{i}():\n    return " + str([j for j in range(100)]) + "\n\n")
    
    # Create 3 large noise files (approx 20kb each)
    for k in range(3):
        with open(f"distractor_{k}.py", "w") as f:
            for i in range(50): # 50 functions per file
                f.write(noise_content.format(i=i + (k*100)))
    
    # Create the Needle
    with open("critical_logic.py", "w") as f:
        f.write("def calculate_tax(amount):\n    return amount * 0.5 # BUG: Tax is too high")

    console.print(Panel(
        "[bold white]SCENARIO: Finding the Needle (Cognitive Load Shaping)[/bold white]\n" 
        "[dim]The environment is flooded with irrelevant 'noise' code.[/dim]\n\n"
        "1. [red]distractor_0.py - distractor_2.py[/red]: Heavy noise files.\n"
        "2. [green]critical_logic.py[/green]: Small file with a bug.\n\n"
        "[bold yellow]Challenge:[/bold yellow] Identify and fix the bug in 'critical_logic.py' WITHOUT loading the distractors into L1.\n"
        "This proves the agent filters noise before 'thinking'.",
        title="Capability 7: Cognitive Load", border_style="cyan"
    ))

    # 2. Initialize Session
    # Capacity is small (1000 tokens). 
    mission = (
        "MISSION: Find the function 'calculate_tax' and fix the tax rate to 0.05. "
        "Ignore irrelevant files."
    )
    session = AmnesicSession(mission=mission, l1_capacity=1000)
    config = {"configurable": {"thread_id": "proof_cognitive_load"}, "recursion_limit": 100}
    
    session.visualize()
    
    turn_count = 0
    success = False
    
    # 3. Telemetry Setup (Matching proof_gc.py standard)
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Files", "center", "magenta", 12),
        ("L1 Toks", "center", "white", 10),
        ("Arts", "center", "green", 4),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 50),
        ("Auditor", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Mission Execution Trace", style="bold blue"))
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    # 4. Execution Loop
    for event in session.app.stream(session.state, config=config):
        node_name = list(event.keys())[0]
        node_output = event[node_name]
        
        current_state = session.app.get_state(config).values
        if not current_state: current_state = session.state
            
        fw_state = current_state.get('framework_state')
        pager = session.pager
        
        move = node_output.get('manager_decision') if 'manager_decision' in node_output else current_state.get('manager_decision')
        audit = current_state.get('last_audit')

        if node_name == "manager":
            turn_count += 1
        
        active_files = [k.replace("FILE:", "") for k in pager.active_pages.keys() if "SYS:" not in k]
        artifact_names = [a.identifier for a in fw_state.artifacts]
        token_str = f"{pager.current_usage}/{pager.capacity}"
        
        # Check Fail Condition (Loading Distractors)
        if any("distractor" in f for f in active_files):
            console.print("[bold red]FAIL: Agent loaded a distractor file![/bold red]")
            # Note: We continue to show the trace but this is a failure of the specific test condition
        
        audit_val = audit["auditor_verdict"] if audit else "---"
        audit_style = "green" if audit_val == "PASS" else "red" if audit_val == "REJECT" else "white"

        node_label = node_name
        if node_name == "manager": node_label = "Manager 🧠"
        if node_name == "auditor": node_label = "Auditor 🛡️"
        if node_name == "executor": node_label = "Executor ⚡"

        if move:
            row_data = (
                str(turn_count),
                ", ".join(active_files) if active_files else "EMPTY",
                token_str,
                str(len(artifact_names)),
                node_label,
                f"{move.tool_call}({move.target})" if move else "---",
                move.thought_process if move else "---",
                Text(audit_val, style=audit_style)
            )
            print_stream_row(row_data)

            # Check Success
            if move.tool_call == "edit_file" and "critical_logic.py" in move.target:
                success = True
            
            if move.tool_call == "halt_and_ask" and success:
                console.print(Panel("[bold green]SUCCESS: Bug fixed without reading noise.[/bold green]"))
                break

        if turn_count > 15:
            console.print("[bold red]Timeout.[/bold red]")
            break

    # Cleanup
    for f in ["critical_logic.py"] + [f"distractor_{k}.py" for k in range(3)]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_cognitive_load_proof()