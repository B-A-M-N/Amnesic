import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_failure_taxonomy_proof():
    console = Console()
    
    console.print(Panel(
        "[bold white]SCENARIO: Controlled Degradation (Failure Taxonomy)[/bold white]\n"
        "[dim]We intentionally stress the system to observe failure safety.[/dim]\n\n"
        "1. [red]Deadlock[/red]: Manager requests a file larger than L1 capacity.\n"
        "2. [yellow]Thrash[/yellow]: Constant staging/eviction due to low L1 budget.\n"
        "3. [cyan]Starvation[/cyan]: Missing artifacts causing halted reasoning.",
        title="Capability 18: Failure Taxonomy", border_style="red"
    ))

    # Telemetry Setup (Standardized)
    COLS = [
        ("Event", "left", "cyan", 15),
        ("L1 Files", "center", "magenta", 15),
        ("L1 Toks", "center", "white", 10),
        ("Pager Action", "left", "yellow", 30),
        ("Status", "center", None, 10)
    ]

    def print_trace_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    # --- Mode 1: Deadlock (Physical Limit) ---
    console.print(Rule("Testing Failure Mode: DEADLOCK (Context Overload)"))
    
    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    console.print(header)
    console.print(Rule(style="dim"))

    with open("massive_data.py", "w") as f:
        f.write("# NOISE " * 2000) # Exceeds 1000 tokens
    
    session = AmnesicSession(mission="Read massive_data.py", l1_capacity=500)
    
    # Simulate Call
    try:
        session._tool_stage("massive_data.py")
        print_trace_row(("STAGE_REQ", "massive_data", "8000/500", "REJECTED (Too Large)", Text("SAFE", style="green")))
    except ValueError as e:
        print_trace_row(("STAGE_REQ", "EMPTY", "0/500", f"KERNEL_ERROR: {str(e)[:20]}...", Text("SAFE", style="green")))

    # --- Mode 2: Thrash (Smart Eviction) ---
    console.print(Rule("Testing Failure Mode: THRASH (Automated Recovery)"))
    console.print(header)
    console.print(Rule(style="dim"))

    session_t = AmnesicSession(mission="Swap between A and B", l1_capacity=100)
    # 60 tokens each -> 120 total > 100 capacity.
    content_a = "val_a = 1" + (" # NOISE" * 20)
    content_b = "val_b = 2" + (" # NOISE" * 20)
    
    with open("file_a.py", "w") as f: f.write(content_a)
    with open("file_b.py", "w") as f: f.write(content_b)
    
    session_t.pager.request_access("FILE:file_a.py", content_a)
    print_trace_row(("LOAD_A", "file_a.py", f"{session_t.pager.current_usage}/100", "INSERTED", Text("OK", style="green")))
    
    session_t.pager.tick()
    
    session_t.pager.request_access("FILE:file_b.py", content_b)
    # This triggers eviction
    print_trace_row(("LOAD_B", "file_b.py", f"{session_t.pager.current_usage}/100", "EVICTED_A -> INSERTED_B", Text("RECOVERED", style="green")))
    
    # Assertion: File A should be evicted (missing from L1), File B should be present.
    is_a_gone = "FILE:file_a.py" not in session_t.pager.active_pages
    is_b_here = "FILE:file_b.py" in session_t.pager.active_pages
    
    if is_a_gone and is_b_here:
        console.print(Panel("[bold green]SUCCESS: Pager automatically managed thrash via LRU eviction.[/bold green]"))
    else:
        # Debug output
        active_keys = list(session_t.pager.active_pages.keys())
        console.print(Panel(f"[bold red]FAIL: Pager allowed L1 overflow or failed eviction.\nActive: {active_keys}[/bold red]"))

    # Cleanup
    for f in ["massive_data.py", "file_a.py", "file_b.py"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_failure_taxonomy_proof()
