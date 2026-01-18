import os
import sys
import logging
from rich.console import Console

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.pipeline import AmnesicPipeline
from amnesic.core.sidecar import SharedSidecar

# Suppress noisy logs
logging.getLogger("amnesic").setLevel(logging.ERROR)

def run_pipeline_proof():
    # 0. Setup Environment
    SharedSidecar().reset()
    if os.path.exists("temp_pipe"):
        import shutil
        shutil.rmtree("temp_pipe")
    os.makedirs("temp_pipe", exist_ok=True)

    # Create dummy files
    files = ["alpha.py", "beta.py", "gamma.py"]
    for f in files:
        with open(f"temp_pipe/{f}", "w") as fh:
            fh.write(f"def process_{f.split('.')[0]}(): return True")

    # 1. Initialize Pipeline
    pipeline = AmnesicPipeline(default_recursion_limit=150)

    # 2. Add Steps
    
    # STEP 1: SCOUT (Fluid)
    # Goal: Generate a comma-separated list of filenames ONLY (no paths)
    pipeline.add_step(
        name="Scout",
        mission=(
            "Scan 'temp_pipe/'. "
            "Save an artifact 'FILE_LIST' containing a comma-separated list of the FILENAMES only (e.g. 'alpha.py,beta.py'). "
            "Do NOT include the 'temp_pipe/' prefix in the list. HALT."
        ),
        profile="FLUID_READ"
    )

    # STEP 2: WORKERS (Map)
    # Goal: Process each file individually
    # {item} will be replaced by 'alpha.py', 'beta.py', etc.
    # We reconstruct the path here: 'temp_pipe/{item}'
    pipeline.add_map_step(
        name="Analyzer Swarm",
        input_artifact="FILE_LIST",
        mission_template=(
            "Read 'temp_pipe/{item}'. "
            "Extract the function name. "
            "Save it as artifact 'FUNC_{item}'. "
            "HALT."
        ),
        profile="FLUID_READ"
    )

    # STEP 3: REPORT (Strict)
    # Goal: Combine results
    pipeline.add_step(
        name="Reporter",
        mission=(
            "1. Use 'calculate' with target 'JOIN' to combine all 'FUNC_' artifacts in your backpack.\n"
            "2. YOU MUST Use 'write_file' with target 'final_report.txt: ARTIFACT:TOTAL' to save the result.\n"
            "3. After successful write, you may stop."
        ),
        profile="STRICT_AUDIT",
        forbidden_tools=["halt_and_ask"]
    )

    # 3. Execute
    try:
        pipeline.run()
    except Exception as e:
        print(f"Pipeline crashed: {e}")

    # 4. Verify
    if os.path.exists("final_report.txt"):
        with open("final_report.txt") as f:
            content = f.read()
        print("\n--- FINAL REPORT ---")
        print(content)
        
        # Check if we got results
        if "process_" in content:
            print("\n[SUCCESS] Pipeline executed map-reduce workflow!")
        else:
            print("\n[FAIL] Report generated but missing data.")
    else:
        # Fallback verification: Check artifacts directly if report failed (Reporter might loop)
        # This proves the Map Step worked even if the Reporter failed
        print("\n[Audit] Checking Map Step Results in Sidecar...")
        # Since we can't easily access the internal sidecar here without digging, we assume fail.
        print("[FAIL] No report generated.")

    # Cleanup
    try:
        import shutil
        shutil.rmtree("temp_pipe")
        if os.path.exists("final_report.txt"): os.remove("final_report.txt")
    except: pass

if __name__ == "__main__":
    run_pipeline_proof()