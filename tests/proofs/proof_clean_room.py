"""
Proof of Concept: The 'Clean Room' (Security Sanitization)
Verifies the architectural capability to ingest sensitive data, 
extract safe patterns, and permanently discard the sensitive context.
"""
import sys
import os
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from amnesic.presets.clean_room import CleanRoomSession

console = Console()

def run_clean_room_proof():
    console.print(Panel(
        "[bold white]SCENARIO: IP Sanitization (The Clean Room)[/bold white]\n"
        "[dim]The Agent must read a proprietary file containing Secrets,[/dim]\n"
        "[dim]extract a safe 'Stub' or 'Interface', and ensure Secrets never persist.[/dim]\n\n"
        "1. [red]Input[/red]: 'secret_core.py' (Contains API Keys & PII).\n"
        "2. [yellow]Process[/yellow]: Extract class structure, redact values.\n"
        "3. [green]Output[/green]: Safe Artifact. L1 Wiped.",
        title="Application: Clean Room", border_style="red"
    ))

    # 1. Create Sensitive File
    secret_code = """
class PaymentProcessor:
    def __init__(self):
        self.api_key = "sk-LIVE-9999-SECRET-DONT-SHARE" # SECRET!
        self.admin_email = "admin@company.com" # PII!
        
    def process_transaction(self, user_id, amount):
        # Proprietary Algorithm
        risk_score = (amount * 0.05) + 42 
        return self._send_to_bank(self.api_key, amount)
        
    def _send_to_bank(self, key, amt):
        print(f"Sending {amt} using {key}")
"""
    with open("secret_core.py", "w") as f:
        f.write(secret_code)

    console.print("[bold]1. Created Sensitive File (secret_core.py)[/bold]")
    console.print(Syntax(secret_code, "python", theme="monokai", line_numbers=True))

    # 2. Initialize Session
    mission = (
        "MISSION: Create a public STUB file (interface only) for 'secret_core.py'. "
        "Keep method signatures. "
        "REPLACE all literal values (strings/numbers) with 'REDACTED'. "
        "REMOVE any internal comments about algorithms."
    )
    
    session = CleanRoomSession(mission=mission, l1_capacity=3000)
    
    # 3. Run (Simulation Loop)
    # We'll use the .stream() via .run() but limited turns
    console.print("\n[bold]2. Engaging Clean Room Agent...[/bold]")
    
    # We manually drive it to ensure we capture the state transitions or just use run()
    # Using a simple loop to check artifacts
    
    config = {"configurable": {"thread_id": "clean_room_proof"}, "recursion_limit": 100}
    
    step_count = 0
    success = False
    
    for event in session.app.stream(session.state, config=config):
        step_count += 1
        current_state = session.app.get_state(config).values
        if not current_state: current_state = session.state
        
        fw = current_state['framework_state']
        
        # Check for Artifacts
        if fw.artifacts:
            last_art = fw.artifacts[-1]
            console.print(f"[Turn {step_count}] Artifact Created: [blue]{last_art.identifier}[/blue]")
            console.print(Panel(last_art.summary, title="Artifact Content", style="blue"))
            success = True
            break
            
        if step_count > 10:
            console.print("[red]Timeout: Agent failed to produce artifact.[/red]")
            break

    # 4. Verify Hygiene
    console.print("\n[bold]3. Security Audit[/bold]")
    
    # Check Artifacts for Secrets
    forbidden = ["sk-LIVE", "admin@company.com", "9999"]
    is_clean = session.verify_hygiene(forbidden)
    
    if is_clean:
        console.print("[bold green]✔ PASS: No secrets found in Artifacts.[/bold green]")
    else:
        console.print("[bold red]✖ FAIL: Secrets leaked into Artifacts![/bold red]")
        sys.exit(1)
        
    # Check L1 Memory (Should be empty of the file)
    l1_files = list(session.pager.active_pages.keys())
    console.print(f"L1 Status: {l1_files}")
    
    # Note: L1 might contain the "Stub" if it was just created, but strictly speaking 
    # the 'secret_core.py' should be evicted if we followed the 'save_artifact' rule which evicts 'FILE:*'
    # The session._tool_worker_task does: "for file_id in active_files: self.pager.evict_to_l2(file_id)"
    
    if any("secret_core.py" in f for f in l1_files):
        console.print("[bold red]✖ FAIL: Source file still in L1 Context![/bold red]")
    else:
        console.print("[bold green]✔ PASS: Source file evicted from L1.[/bold green]")

    # Cleanup
    if os.path.exists("secret_core.py"): os.remove("secret_core.py")

if __name__ == "__main__":
    run_clean_room_proof()
