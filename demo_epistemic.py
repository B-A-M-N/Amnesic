from amnesic.core.session import AmnesicSession
import os

def run_epistemic_demo():
    # 1. Initialize the Epistemic Session pointing to the current project
    session = AmnesicSession(
        system_prompt="You are a strict architect. Analyze the project structure and explain the Auditor's role.",
        target_dir=".",
        max_turns=5
    )
    
    mission = "Explain the logic inside amnesic/decision/auditor.py"
    
    print(f"Starting Mission: '{mission}'")
    
    try:
        final_state = session.chat(mission)
        
        print("\n=== FINAL EPISTEMIC REPORT ===")
        print(f"Status: {'HALTED' if final_state['global_uncertainty'] > 0.8 else 'COMPLETED'}")
        print(f"Global Uncertainty: {final_state['global_uncertainty']:.2f}")
        
        print("\nDecision History Trace:")
        for trace in final_state.get('decision_history', []):
            status = "✅" if trace['auditor_verdict'] == "PASS" else "❌"
            print(f"{status} Step {trace['step']}: {trace['tool_call']}")
            print(f"    Rationale: {trace['rationale']}")
            print(f"    Conf: {trace['confidence_score']:.2f}")
            
    except Exception as e:
        print(f"\nExecution Error: {e}")

if __name__ == "__main__":
    run_epistemic_demo()