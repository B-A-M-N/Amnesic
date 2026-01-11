"""
Proof of Concept: Prefetching (L2 Cache Optimization)
Verifies the 'prefetch' capability which allows loading future context into RAM (L2)
without polluting the active Context Window (L1).
"""
import sys
import os
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from amnesic.core.dynamic_pager import DynamicPager

console = Console()

def print_state_table(step_name: str, pager: DynamicPager):
    """
    Renders the current memory state (L1 vs L2).
    """
    table = Table(title=f"Memory State: {step_name}", expand=True, border_style="dim")
    table.add_column("Page ID", style="cyan", no_wrap=True)
    table.add_column("Location", justify="center", style="bold")
    table.add_column("Tokens", justify="right", style="magenta")
    table.add_column("Status", justify="left")

    # L1 Pages
    for pid, page in pager.l1_active.items():
        table.add_row(pid, "[green]L1 (Active)[/green]", str(page.tokens), "In Context Window")
    
    # L2 Pages
    for pid, page in pager.l2_staging.items():
        table.add_row(pid, "[yellow]L2 (Staged)[/yellow]", str(page.tokens), "In RAM (Ready)")

    console.print(table)

def run_prefetch_proof():
    console.print(Panel(
        "[bold white]SCENARIO: Predictive Prefetching[/bold white]\n"
        "[dim]Simulating a workflow where the Agent is busy with File A,[/dim]\n"
        "[dim]but expects to need File B next. We load File B into L2 silently.[/dim]\n\n"
        "1. [cyan]Active Work[/cyan]: Processing 'main.py' (L1).\n"
        "2. [yellow]Prefetch[/yellow]: Background load 'utils.py' to L2.\n"
        "3. [green]Promotion[/green]: Instant swap when 'utils.py' is requested.",
        title="Optimization Proof: Prefetching", border_style="blue"
    ))

    # 1. Setup
    pager = DynamicPager(capacity_tokens=1000)
    
    console.print(Panel("[bold]Step 1: Active Work (L1)[/bold]", style="cyan"))
    pager.request_access("FILE:main.py", "print('Processing main logic...')")
    
    print_state_table("Processing main.py", pager)
    time.sleep(1)

    # 2. Prefetch
    console.print(Panel("[bold]Step 2: Prefetch 'utils.py' (L2)[/bold]", style="yellow"))
    pager.prefetch("FILE:utils.py", "def helper(): pass\n" * 50) # ~500 chars -> ~125 tokens
    
    # Verify it's in L2 but NOT L1
    in_l2 = "FILE:utils.py" in pager.l2_staging
    not_in_l1 = "FILE:utils.py" not in pager.l1_active
    
    if in_l2 and not_in_l1:
        console.print("[bold green]✔ Prefetch Successful (Staged in L2)[/bold green]")
    else:
        console.print("[bold red]✖ Prefetch Failed[/bold red]")
        sys.exit(1)
        
    print_state_table("After Prefetch", pager)
    time.sleep(1)

    # 3. Promotion (Cache Hit)
    console.print(Panel("[bold]Step 3: Request 'utils.py' (Promotion)[/bold]", style="green"))
    console.print("[dim]Simulating Manager requesting the next file...[/dim]")
    
    # Request WITHOUT content - forcing it to rely on L2 cache
    found = pager.request_access("FILE:utils.py") 
    
    if found:
        console.print("[bold green]✔ Cache Hit! Promoted from L2 without disk I/O.[/bold green]")
    else:
        console.print("[bold red]✖ Cache Miss! Failed to find in L2.[/bold red]")
        sys.exit(1)

    print_state_table("After Promotion", pager)
    
    # Final check: main.py might still be there if space permits, or evicted.
    # Capacity 1000. main.py is tiny. utils.py is ~125. Both fit.
    if "FILE:main.py" in pager.l1_active and "FILE:utils.py" in pager.l1_active:
         console.print("[dim]Note: Both files fit in L1 context.[/dim]")

    console.print(Panel("[bold green]PROOF SUCCESSFUL: Prefetching mechanism verified.[/bold green]"))

if __name__ == "__main__":
    run_prefetch_proof()
