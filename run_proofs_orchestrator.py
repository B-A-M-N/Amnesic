import subprocess
import sys
import time
import os

TEST_FILES = [
    "tests/proofs/advanced_semantic_proof.py",
    "tests/proofs/basic_semantic_proof.py",
    "tests/proofs/proof_clean_room.py",
    "tests/proofs/proof_code_advanced.py",
    "tests/proofs/proof_code_basic.py",
    "tests/proofs/proof_cognitive_load.py",
    "tests/proofs/proof_comparator.py",
    "tests/proofs/proof_context_offloading.py",
    "tests/proofs/proof_contracts.py",
    "tests/proofs/proof_determinism.py",
    "tests/proofs/proof_elastic_context.py",
    "tests/proofs/proof_extreme_efficiency.py",
    "tests/proofs/proof_failure_taxonomy.py",
    "tests/proofs/proof_gc.py",
    "tests/proofs/proof_hive_mind.py",
    "tests/proofs/proof_human_friction.py",
    "tests/proofs/proof_ignorance.py",
    "tests/proofs/proof_isolation.py",
    "tests/proofs/proof_marathon.py",
    "tests/proofs/proof_mediator.py",
    "tests/proofs/proof_model_invariance.py",
    "tests/proofs/proof_persona_swap.py",
    "tests/proofs/proof_prefetch.py",
    "tests/proofs/proof_rosetta.py",
    "tests/proofs/proof_self_correction.py",
    "tests/proofs/proof_time_travel.py",
    "tests/proofs/proof_workspace_nexus.py",
    "tests/proofs/real_stress_test.py",
    "tests/proofs/red_team_proof.py",
    "tests/proofs/test_policies.py"
]

def run_test(test_path):
    print(f"Running {test_path}...")
    start_time = time.time()
    try:
        # Run with a timeout of 60 seconds to detect hangs (optional, but good practice)
        # Using sys.executable ensures we use the same python interpreter
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        duration = time.time() - start_time
        if result.returncode == 0:
            return "PASS", duration, result.stdout
        else:
            return "FAIL", duration, result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return "TIMEOUT", duration, "Timed out"

def main():
    results = {}
    
    for test_file in TEST_FILES:
        if not os.path.exists(test_file):
            print(f"Skipping {test_file} (File not found)")
            continue
            
        status = "FAIL"
        output_log = ""
        
        # Try up to 3 times
        for attempt in range(1, 4):
            print(f"[{test_file}] Attempt {attempt}/3")
            status, duration, output = run_test(test_file)
            
            if status == "PASS":
                print(f"  -> PASS ({duration:.2f}s)")
                break
            else:
                print(f"  -> {status} ({duration:.2f}s)")
                output_log = output # Keep the last failure log
                if attempt < 3:
                    print("     Retrying...")
        
        results[test_file] = status
        
        if status != "PASS":
             print(f"\n--- Output for {test_file} ---\n{output_log}\n--------------------------------\n")

    print("\n\nSUMMARY:")
    print("========================================")
    for test_file, status in results.items():
        print(f"{test_file}: {status}")

if __name__ == "__main__":
    main()
