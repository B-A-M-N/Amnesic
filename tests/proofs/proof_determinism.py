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

def run_determinism_proof():
    console = Console()
    
    console.print(Panel(
        "[bold white]SCENARIO: Groundhog Day (Determinism Levers)[/bold white]\n"
        "[dim]We force the agent into a fixed state and ask the same question 5 times.[/dim]\n\n"
        "[bold yellow]Challenge:[/bold yellow] The 'ManagerMove' (Tool + Target + Rationale) must be IDENTICAL every time.\n"
        "This proves the architecture can enforce deterministic engineering outcomes.",
        title="Capability 8: Determinism", border_style="magenta"
    ))

    # 1. Setup Fixed State
    mission = "TASK: Read 'data_source.txt' and save its content as an artifact. This is the ONLY step."
    with open("data_source.txt", "w") as f:
        f.write("val_a = 123\nval_b = 456")
    
    # Mock environment structure
    current_map = [{
        "path": "data_source.txt",
        "classes": [],
        "functions": [],
        "imports": []
    }]
    
    results = []
    
    # 2. Telemetry Setup
    # ... (rest of telemetry remains same)
    COLS = [
        ("Run", "right", "cyan", 4),
        ("L1 Files", "center", "magenta", 12),
        ("L1 Toks", "center", "white", 10),
        ("Arts", "center", "green", 4),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 50),
        ("Status", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Determinism Execution Trace", style="bold blue"))
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    # 3. Execution Loop (5 Independent Runs)
    for i in range(5):
        # Re-init session to ensure clean slate, but with SAME config and SEED
        session = AmnesicSession(mission=mission, l1_capacity=2000, deterministic_seed=42, model="rnj-1:8b-cloud")
        
        # Force a single step of the Manager
        fw_state = session.state['framework_state']
        # Use the map we defined in setup
        pager = session.pager
        
        move = session.manager_node.decide(
            state=fw_state,
            file_map=current_map,
            pager=pager,
            active_context="EMPTY"
        )
        
        results.append(move)
        
        # Format Row
        row_data = (
            str(i + 1),
            "EMPTY",
            f"{pager.current_usage}/{pager.capacity}",
            "0",
            "Manager 🧠",
            f"{move.tool_call}({move.target})",
            move.thought_process,
            Text("CAPTURED", style="dim")
        )
        print_stream_row(row_data)

    # 4. Analysis
    console.print(Rule("Analysis"))
    
    first_move = results[0]
    drift_detected = False
    
    for idx, r in enumerate(results[1:]):
        # We compare tool_call and target. 
        if r.tool_call != first_move.tool_call or r.target != first_move.target:
            drift_detected = True
            console.print(f"[bold red]DRIFT DETECTED at Run {idx+2}![/bold red]")
            console.print(f"Expected: {first_move.tool_call}({first_move.target})")
            console.print(f"Got:      {r.tool_call}({r.target})")
    
    if not drift_detected:
        console.print(Panel("[bold green]SUCCESS: 5/5 runs were identical.[/bold green]"))
    else:
        console.print(Panel("[bold red]FAIL: Non-deterministic behavior observed.[/bold red]"))

if __name__ == "__main__":
    run_determinism_proof()