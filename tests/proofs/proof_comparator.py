import sys
import os
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live

# Ensure we can import amnesic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from amnesic.core.dynamic_pager import DynamicPager
from amnesic.core.comparator import Comparator

console = Console()

def print_state_table(step_name: str, pager: DynamicPager, status: str = "RUNNING"):
    """
    Renders the current memory state as a table.
    """
    table = Table(title=f"Memory State: {step_name}", expand=True, border_style="dim")
    table.add_column("Page ID", style="cyan", no_wrap=True)
    table.add_column("Tokens", justify="right", style="magenta")
    table.add_column("Priority", justify="right", style="green")
    table.add_column("Status", justify="center", style="bold")

    active_pages = pager.active_pages
    
    total_tokens = 0
    for pid, page in active_pages.items():
        total_tokens += page.tokens
        is_pinned = "📌" if page.pinned else ""
        table.add_row(
            f"{pid} {is_pinned}",
            str(page.tokens),
            str(page.priority),
            "ACTIVE (L1)"
        )
    
    # Summary Row
    usage_color = "green" if total_tokens < pager.capacity else "red"
    table.add_row(
        "[bold]TOTAL USAGE[/bold]", 
        f"[{usage_color}]{total_tokens}/{pager.capacity}[/{usage_color}]", 
        "", 
        f"[{usage_color}]{status}[/{usage_color}]",
        end_section=True
    )
    
    console.print(table)

def run_comparator_proof():
    console.print(Panel(
        "[bold white]SCENARIO: The 'Diff' Operation (Dual-Slot Memory)[/bold white]\n"
        "[dim]Verifying the Comparator's ability to temporarily hold two conflicting files in L1 for analysis,[/dim]\n"
        "[dim]and strictly enforcing a 'Double Eviction' afterwards to prevent state pollution.[/dim]\n\n"
        "1. [cyan]Context Load[/cyan]: System + Old Work.\n"
        "2. [yellow]Dual Load[/yellow]: Force load File A and File B (Comparator Mode).\n"
        "3. [red]Purge[/red]: Evict both immediately after verify.",
        title="Component Proof: Comparator", border_style="blue"
    ))

    # 1. Setup
    pager = DynamicPager(capacity_tokens=1000)
    comparator = Comparator(pager)
    
    console.print(Panel("[bold]Step 1: Initial Context Population[/bold]", style="blue"))
    pager.pin_page("SYS:INSTRUCTIONS", "You are an AI assistant.") 
    pager.request_access("FILE:old_work.txt", "Old context that should be evicted.")
    
    print_state_table("Initial State", pager)
    time.sleep(1)

    # 2. Dual Load
    console.print(Panel("[bold]Step 2: Comparator Dual-Load Request[/bold]", style="yellow"))
    file_a = "v1.py"
    content_a = "def hello():\n    print('Hello World')" * 20 
    file_b = "v2.py"
    content_b = "def hello():\n    print('Hello Earth')" * 20
    
    success = comparator.load_pair(file_a, content_a, file_b, content_b)
    
    if success:
        console.print("[bold green]✔ Dual-Load Successful[/bold green]")
        print_state_table("Comparator Active", pager, status="OVERLOAD ALLOWED" if pager.current_usage > pager.capacity else "OK")
    else:
        console.print("[bold red]✖ Dual-Load Failed[/bold red]")
        sys.exit(1)

    # Verify Assertions visually
    passed = "FILE:old_work.txt" not in pager.active_pages and f"FILE:{file_a}" in pager.active_pages
    console.print(f"Assertion (Old Work Evicted): [{'green' if passed else 'red'}]{passed}[/]")
    
    time.sleep(1)

    # 3. OOM Check
    console.print(Panel("[bold]Step 3: OOM Protection Test[/bold]", style="magenta"))
    huge_content = "x" * 2500 
    oom_success = comparator.load_pair("huge_a", huge_content, "huge_b", huge_content)
    
    if not oom_success:
        console.print("[bold green]✔ OOM Protection Verified (Load Rejected)[/bold green]")
    else:
        console.print("[bold red]✖ OOM Fail: Accepted huge files[/bold red]")

    # 4. Purge
    console.print(Panel("[bold]Step 4: Post-Operation Purge[/bold]", style="red"))
    comparator.purge_pair()
    
    print_state_table("After Purge", pager, status="CLEAN")
    
    # Final Assertions
    clean = f"FILE:{file_a}" not in pager.active_pages and "SYS:INSTRUCTIONS" in pager.active_pages
    console.print(f"Assertion (Context Clean): [{'green' if clean else 'red'}]{clean}[/]")

    if clean:
        console.print(Panel("[bold green]PROOF SUCCESSFUL: Comparator maintains strict hygiene.[/bold green]"))
    else:
        console.print(Panel("[bold red]PROOF FAILED: Leaked context detected.[/bold red]"))

if __name__ == "__main__":
    run_comparator_proof()
