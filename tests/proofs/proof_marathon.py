import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_marathon_proof():
    console = Console()
    
    # 1. Setup: A deep dependency chain (10 files)
    # Each file contains a piece of a sentence.
    sentence_parts = ["The", "Amnesic", "Protocol", "Enables", "Reliable", "Long", "Horizon", "Reasoning", "Without", "Drift"]
    
    for i, part in enumerate(sentence_parts):
        with open(f"step_{i}.txt", "w") as f:
            f.write(f"PART_{i} = '{part}'")
            if i < len(sentence_parts) - 1:
                f.write(f"\n# Next piece is in step_{i+1}.txt")

    console.print(Panel(
        "[bold white]SCENARIO: The Marathon Session (Infinite Horizon)[/bold white]\n"
        "[dim]The agent must traverse a deep chain of 10 dependencies.[/dim]\n\n"
        "[bold yellow]Challenge:[/bold yellow] Successfully reconstruct the 10-word sentence.\n"
        "This requires at least 30-40 graph steps (Map -> Read -> Extract -> Forget * 10).\n"
        "A standard agent would fail due to context window saturation.",
        title="Capability 14: Infinite Horizon",
        border_style="blue"
    ))

    # 2. Initialize Session
    mission = (
        "MISSION: 1. You must reconstruct a 10-word sentence by following a trail of files.\n"
        "2. Start with step_0.txt. Extract PART_0 and IMMEDIATELY use 'save_artifact' to store it. Do NOT unstage until saved.\n"
        "3. Once PART_0 is saved, unstage step_0.txt and move to step_1.txt.\n"
        "4. Repeat this for all 10 files (step_0 through step_9).\n"
        "5. Once you have 10 artifacts, combine them and HALT."
    )
    
    session = AmnesicSession(mission=mission, l1_capacity=2000)
    # Marathon needs high recursion limit
    config = {"configurable": {"thread_id": "proof_marathon"}, "recursion_limit": 300}
    
    session.visualize()
    
    turn_count = 0
    
    # 3. Telemetry
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 File", "center", "magenta", 12),
        ("Arts Found", "center", "green", 30),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 40)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Marathon Trace (Deep Dependency Chain)", style="bold blue"))
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
        
        if node_name == "manager":
            turn_count += 1
        
        pager = session.pager
        move = node_output.get('manager_decision') if 'manager_decision' in node_output else current_state.get('manager_decision')
        fw_state = current_state.get('framework_state')
        
        active_files = [k.replace("FILE:", "") for k in pager.active_pages.keys() if "SYS:" not in k]
        artifact_ids = [a.identifier for a in fw_state.artifacts]
        
        if move:
            row_data = (
                str(turn_count),
                active_files[0] if active_files else "EMPTY",
                ", ".join(artifact_ids) if artifact_ids else "None",
                node_name,
                f"{move.tool_call}({move.target})",
                move.thought_process
            )
            print_stream_row(row_data)

            if move.tool_call == "halt_and_ask":
                # Check for completeness
                parts_found = len([a for a in fw_state.artifacts if "PART_" in a.identifier])
                if parts_found >= 10:
                    console.print(Panel(f"[bold green]SUCCESS: Marathon complete. Turn {turn_count}. Sentence: {move.target}[/bold green]"))
                else:
                    console.print(Panel(f"[bold red]FAIL: Marathon failed. Only found {parts_found}/10 parts.[/bold red]"))
                break
        
        if turn_count > 100:
            console.print("[bold red]Timeout: Session too long.[/bold red]")
            break

    # Cleanup
    for i in range(10):
        f = f"step_{i}.txt"
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_marathon_proof()
