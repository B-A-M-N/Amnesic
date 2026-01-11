import os
import sys
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_control_determinism():
    console = Console()
    
    console.print(Panel(
        "[bold white]SCENARIO: Chaos Theory (Control: Determinism)[/bold white]\n"
        "[dim]We run the agent 5 times WITHOUT the deterministic seed.[/dim]\n\n"
        "[bold yellow]Hypothesis:[/bold yellow] The 'ManagerMove' will drift (change thought/tool) due to LLM temperature > 0.",
        title="Control: Determinism", border_style="red"
    ))

    mission = "Calculate 123 * 456."
    results = []
    
    COLS = [
        ("Run", "right", "cyan", 4),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 50),
        ("Status", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Execution Trace (Control)", style="bold red"))
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    # Run 5 times with DEFAULT temperature (usually 0.7 or 0.1 depending on driver default, but not 0.0)
    for i in range(5):
        # NO deterministic_seed passed
        session = AmnesicSession(mission=mission, l1_capacity=2000)
        
        fw_state = session.state['framework_state']
        current_map = [] 
        pager = session.pager
        
        move = session.manager_node.decide(
            state=fw_state,
            file_map=current_map,
            pager=pager,
            active_context="EMPTY"
        )
        
        results.append(move)
        
        row_data = (
            str(i + 1),
            f"{move.tool_call}({move.target})",
            move.thought_process,
            Text("CAPTURED", style="dim")
        )
        print_stream_row(row_data)

    # Analysis
    console.print(Rule("Analysis"))
    
    first_move = results[0]
    drift_detected = False
    
    # We check for EXACT match. Even a slight change in thought process is "Drift".
    # In the deterministic proof, we demanded identical tool+target.
    # Here, we expect *some* variance, likely in the thought process text.
    
    for idx, r in enumerate(results[1:]):
        if r.thought_process != first_move.thought_process:
            drift_detected = True
            console.print(f"[bold green]DRIFT DETECTED at Run {idx+2}:[/bold green] Thought process diverged.")
        elif r.tool_call != first_move.tool_call:
            drift_detected = True
            console.print(f"[bold green]DRIFT DETECTED at Run {idx+2}:[/bold green] Tool call diverged.")

    if drift_detected:
        console.print(Panel("[bold green]SUCCESS: Control proof demonstrated drift (Non-Deterministic).[/bold green]"))
    else:
        console.print(Panel("[bold yellow]FAIL: Output was identical (Agent is naturally deterministic?).[/bold yellow]"))

if __name__ == "__main__":
    run_control_determinism()
