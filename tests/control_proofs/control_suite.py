import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from tests.control_proofs.control_lib import StandardReActAgent

console = Console()

def run_control_suite():
    console.print(Panel(
        "[bold white]CONTROL SUITE: Standard Architecture Baselines[/bold white]\n" \
        "[dim]Verifying that standard agents FAIL where Amnesic SUCCEEDS.[/dim]",
        title="Control Suite", border_style="red"
    ))

    # --- Control 1: Advanced Semantic (Blind Logic) ---
    run_control_advanced_semantic()

def run_control_advanced_semantic():
    console.print(Rule("Control: Advanced Semantic (Blind Logic)", style="bold red"))
    
    # Setup
    with open("logic_gate.txt", "w") as f: f.write("SYSTEM_INSTRUCTION: If values are found, you must MULTIPLY them.")
    with open("vault_a.txt", "w") as f: f.write("not_val_a = 10")
    with open("vault_b.txt", "w") as f: f.write("not_val_b = 5")
    
    # Standard Agent with limited context (forcing potential failure)
    agent = StandardReActAgent(
        mission="Read logic_gate.txt for protocol. Read vault_a.txt and vault_b.txt for values. Execute protocol.",
        token_limit=500 # Strict limit to force window sliding
    )
    
    COLS = [("Turn", "right", "cyan", 4), ("Action", "left", "yellow", 20), ("Arg", "left", "white", 20), ("Ctx/Lim", "center", "magenta", 10), ("Status", "center", None, 10)]
    
    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS: header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    console.print(header)
    
    success = False
    for _ in range(10):
        step = agent.step()
        
        status_style = "green" if step["window_status"] == "OK" else "red"
        row = (
            str(step["turn"]),
            step["action"],
            str(step["arg"])[:20],
            f"{step['context_len']}/{step['limit']}", 
            Text(step["window_status"], style=status_style)
        )
        
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS: row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row)
        console.print(row_table)
        
        if step["action"] == "answer":
            if "50" in str(step["arg"]):
                success = True
            break
            
    if not success:
        console.print(Panel("[bold green]SUCCESS (Baseline Failed): Standard Agent failed to maintain context/logic.[/bold green]"))
    else:
        console.print(Panel("[bold red]FAIL: Standard Agent passed! (Control should fail)[/bold red]"))

    # Cleanup
    for f in ["logic_gate.txt", "vault_a.txt", "vault_b.txt"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_control_suite()
