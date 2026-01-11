from amnesic.core.session import AmnesicSession
import logging

# Configure logging to see the driver in action
logging.basicConfig(level=logging.INFO)

def run_final_demo():
    print("=== AMNESIC FRAMEWORK V1.0 ===")
    
    # 1. Initialize Session
    # Pointing to the current directory to scan itself
    session = AmnesicSession(
        system_prompt="You are an expert python developer.",
        target_dir=".",
        max_turns=6
    )
    
    # 2. Define Mission
    # A task that requires seeing structure (finding a file) and reasoning
    mission = "Find the file that handles the 'Sanitizer' logic and read its content."
    
    print(f"Mission: {mission}")
    
    try:
        # 3. Execute
        final_state = session.chat(mission)
        
        # 4. Report
        print("\n=== MISSION COMPLETE ===")
        print(f"Global Uncertainty: {final_state['global_uncertainty']:.2f}")
        
        print("\nTrace:")
        for trace in final_state.get('decision_history', []):
            verdict = "✅" if trace['auditor_verdict'] == "PASS" else "❌"
            print(f"{verdict} {trace['tool_call']} (Conf: {trace['confidence_score']:.2f})")
            
    except Exception as e:
        print(f"\nCRITICAL FAILURE: {e}")

if __name__ == "__main__":
    run_final_demo()
