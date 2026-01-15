import os
import shutil
import logging
from rich.console import Console
from rich.panel import Panel

# Ensure framework access
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

# Suppress noise
logging.getLogger("amnesic").setLevel(logging.ERROR)

def run_overflow_proof():
    console = Console()
    console.print(Panel.fit("[bold red]PROOF: NATIVE WINDOW OVERFLOW[/bold red]", border_style="red"))
    console.print("[dim]Scenario: Data Size (40k tokens) > L1 Capacity (25k tokens)[/dim]")

    # 1. Setup Data: 16 files * 2.5k tokens = 40k tokens
    # L1 Limit is 25k. The agent MUST offload.
    data_dir = "overflow_data"
    if os.path.exists(data_dir): shutil.rmtree(data_dir)
    os.makedirs(data_dir, exist_ok=True)
    
    expected_sum = 0
    console.print("Generating heavy dataset...", end=" ")
    for i in range(16):
        val = 10 + i
        expected_sum += val
        with open(f"{data_dir}/log_{i:02d}.txt", "w") as f:
            # Padding to consume tokens (~2.5k tokens per file)
            # 1 token ~= 4 chars. 2500 tokens ~= 10,000 chars.
            noise = "PROCESS_TRACE_DUMP_HEX_BLOCK " * 500 
            f.write(noise + "\n")
            f.write(f"TARGET_VALUE: {val}\n")
            f.write(noise)
    console.print("[Done]")

    # 2. Initialize Session with Native-like Capacity
    # Using dynamic partitioning: 32k Total.
    # L1 (Input) = 50% = 16384 tokens.
    # Reasoning (Output) = 40% = 13107 tokens.
    # Overhead = 10% = 3276 tokens.
    # This provides MASSIVE reasoning space compared to the previous run.
    session = AmnesicSession(
        mission=(
            "Scan 'overflow_data/' (files log_00.txt to log_15.txt). "
            "For EACH file, extract 'TARGET_VALUE' (integer) and save it as a UNIQUE artifact named 'VAL_<filename>' (e.g., 'VAL_log_00.txt'). "
            "DO NOT overwrite artifacts you already have. "
            "Once you have saved ALL 16 values, use 'calculate' to SUM the integers. HALT."
        ),
        root_dir=data_dir,
        max_total_context=32768,
        context_ratios={"input": 0.5, "output": 0.4, "overhead": 0.1},
        audit_profile="FLUID_READ", # Speed is essential here
        elastic_mode=True # Allow multiple files, forcing it to hit the limit
    )

    # 3. Execution
    console.print("\n[bold]Running Overflow Mission...[/bold]")
    try:
        # High recursion limit because reading 16 files takes many turns
        session.run(config={"recursion_limit": 150, "configurable": {"thread_id": "overflow"}})
    except Exception as e:
        console.print(f"[red]Session Crashed:[/red] {e}")

    # 4. Audit
    console.print("\n--- Artifact Audit ---")
    final_sum = 0
    found_count = 0
    
    # Check for a total
    for art in session.state['framework_state'].artifacts:
        console.print(f"- {art.identifier}: {art.summary}")
        if "TOTAL" in art.identifier:
            try:
                # Extract number from summary
                import re
                nums = re.findall(r'\d+', art.summary)
                if nums: final_sum = int(nums[0])
            except: pass
        
        # Check individual extractions if total failed
        if any(kw in art.identifier.upper() for kw in ["TARGET", "VALUE", "VAL_"]):
            found_count += 1

    console.print(f"\nExpected Sum: {expected_sum}")
    console.print(f"Agent Found:  {final_sum}")
    
    if final_sum == expected_sum:
        console.print("[bold green]PROOF SUCCESS: Perfect recall across overflowed context![/bold green]")
    elif found_count >= 16:
        console.print("[bold yellow]PARTIAL SUCCESS: All files processed, but sum calculation failed.[/bold yellow]")
    else:
        console.print(f"[bold red]PROOF FAILED: Processed only {found_count}/16 files.[/bold red]")

    # Cleanup
    shutil.rmtree(data_dir)

if __name__ == "__main__":
    run_overflow_proof()
