import os
import sys
import random
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_self_correction_proof():
    console = Console()
    
    # 1. Setup: Contradictory Information
    # File A has a misleading comment. File B has the truth.
    with open("source_a.py", "w") as f:
        f.write("# THE_SECRET = 9999 (Verified by Admin)\n# Legacy note: ignore above, use 1234")
    
    with open("source_b.py", "w") as f:
        f.write("# SECURITY AUDIT: source_a.py legacy note is a decoy.\n# THE_SECRET is actually 8888.")

    console.print(Panel(
        "[bold white]SCENARIO: Semantic Self-Correction (The Oops Proof)[/bold white]\n"
        "[dim]The agent encounters contradictory information and must correct its memory.[/dim]\n\n"
        "1. [cyan]source_a.py[/cyan]: Mentions 1234 as the secret (Decoy).\n"
        "2. [green]source_b.py[/green]: Reveals 1234 is a decoy and 8888 is the truth.\n\n"
        "[bold yellow]Challenge:[/bold yellow] Agent initially saves 'THE_SECRET=1234'. "
        "Upon reading source_b.py, it must RE-SAVE the artifact with 8888.",
        title="Capability 13: Self-Correction",
        border_style="magenta"
    ))

    # 2. Initialize Session
    mission = (
        "MISSION: 1. Extract 'THE_SECRET' from source_a.py.\n"
        "2. Read source_b.py. If 'THE_SECRET' is different, update it using the protocol.\n"
        "3. PROTOCOL: Save new value to 'TEMP_VAL', delete 'THE_SECRET', stage 'TEMP_VAL', then save 'THE_SECRET'.\n"
        "4. HALT only after THE_SECRET is saved as 8888."
    )
    
    session = AmnesicSession(mission=mission, l1_capacity=2000)
    config = {"configurable": {"thread_id": "proof_self_correction"}, "recursion_limit": 100}
    
    session.visualize()
    
    # 3. Telemetry Setup
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Contents", "center", "magenta", 20),
        ("Arts", "center", "green", 15),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 40),
        ("Auditor", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Self-Correction Trace: Semantic Bridging", style="bold magenta"))
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    turn_count = 0
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
        
        active_pages = [k.replace("FILE:", "") for k in pager.active_pages.keys() if "SYS:" not in k]
        artifact_ids = [a.identifier for a in fw_state.artifacts]
        
        audit_val = audit["auditor_verdict"] if audit else "---"
        audit_style = "green" if "PASS" in str(audit_val) else "red" if "REJECT" in str(audit_val) else "white"

        if move:
            row_data = (
                str(turn_count),
                ", ".join(active_pages) if active_pages else "EMPTY",
                ", ".join(artifact_ids) if artifact_ids else "None",
                node_name,
                f"{move.tool_call}({move.target})",
                move.thought_process,
                Text(str(audit_val), style=audit_style)
            )
            print_stream_row(row_data)

            if move.tool_call == "halt_and_ask":
                # Final Verification
                final_secret = next((a.summary for a in fw_state.artifacts if a.identifier == "THE_SECRET"), "")
                if "8888" in final_secret:
                    console.print(Panel(f"[bold green]SUCCESS: Artifact corrected to {final_secret}.[/bold green]"))
                else:
                    console.print(Panel(f"[bold red]FAIL: Secret is still '{final_secret}'. Artifacts: {artifact_ids}[/bold red]"))
                break
        
        if turn_count > 30:
            console.print("[bold red]Timeout.[/bold red]")
            break

    # Cleanup
    for f in ["source_a.py", "source_b.py"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_self_correction_proof()
