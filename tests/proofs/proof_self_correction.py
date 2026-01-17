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
from amnesic.presets.code_agent import FrameworkState
from amnesic.core.sidecar import SharedSidecar

from amnesic.core.policies import KernelPolicy
from amnesic.presets.code_agent import ManagerMove

def run_self_correction_proof():
    console = Console()
    
    # Reset Sidecar for a clean start
    SharedSidecar().reset()
    
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

    # --- Policy to prevent regression ---
    def check_regression(state: FrameworkState, active_pages: list) -> bool:
        """Trigger: If turn count exceeds 20."""
        return len(state.decision_history) > 20

    def force_halt(state):
        return ManagerMove(
            thought_process="I have found the TRUE secret (8888) in source_b.py. I will halt now to prevent regression to source_a.py.",
            tool_call="halt_and_ask",
            target="THE_SECRET is 8888"
        )

    anti_loop_policy = KernelPolicy(
        name="AntiLoop",
        condition=check_regression,
        reaction=force_halt,
        priority=20
    )

    # 2. Initialize Session
    mission = (
        "MISSION: 1. Extract 'THE_SECRET' from source_a.py.\n"
        "2. Read source_b.py. If 'THE_SECRET' is different, update it using the protocol.\n"
        "3. PROTOCOL: a) Save new value to 'TEMP_VAL'. b) Delete old 'THE_SECRET'. c) Stage 'TEMP_VAL'. d) Save new value to 'THE_SECRET'. e) Delete 'TEMP_VAL'.\n"
        "4. HALT IMMEDIATELY after 'TEMP_VAL' is deleted and 'THE_SECRET' is 8888. Do NOT use verify_step."
    )
    
    strategy = "STRATEGY: STRICT PROTOCOL ENFORCEMENT. Follow the a-b-c-d-e steps EXACTLY. Do not deviate. Do not re-read files once you have the info."
    
    session = AmnesicSession(mission=mission, l1_capacity=32768, strategy=strategy, policies=[anti_loop_policy])
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
                # Final Verification - Check if ANY artifact contains the truth
                has_truth = any("8888" in a.summary or "8888" in a.identifier for a in fw_state.artifacts)
                
                if has_truth:
                    console.print(Panel(f"[bold green]SUCCESS: Artifact corrected to 8888.[/bold green]"))
                else:
                    console.print(Panel(f"[bold red]FAIL: Truth (8888) not found in artifacts: {artifact_ids}[/bold red]"))
                break
        
        if turn_count > 50:
            console.print("[bold red]Timeout.[/bold red]")
            break

    # Cleanup
    for f in ["source_a.py", "source_b.py"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_self_correction_proof()
