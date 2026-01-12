import logging
import re
import os
from typing import List, Literal, TypedDict, Optional, Any
from pydantic import BaseModel, Field
from fastembed import TextEmbedding
import numpy as np

from ..drivers.ollama import OllamaDriver
from ..presets.code_agent import AUDITOR_SYSTEM_PROMPT, AuditorVerdict

logger = logging.getLogger("amnesic.auditor")

# --- 2. The Logic Engine ---
class Auditor:
    def __init__(self, goal: str, constraints: List[str], driver: OllamaDriver, elastic_mode: bool = False):
        self.goal = goal
        self.constraints = constraints
        self.driver = driver
        self.elastic_mode = elastic_mode
        
        # Layer 1: Vector Model (Relevance)
        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.goal_vector = list(self.embedder.embed([goal]))[0]

    def _check_numerical_accuracy(self, claim: str, context: str) -> bool:
        """Verifies that any number mentioned in the claim exists in context."""
        numbers_in_claim = re.findall(r'\b\d+\b', claim)
        if not numbers_in_claim: return True
        context_lower = context.lower()
        for num in numbers_in_claim:
            if num not in context_lower: return False
        return True

    def _check_grounding(self, value: str, context: str) -> bool:
        """Checks if the specific value string is present in the context."""
        if not value or not context: return False
        clean_val = value.strip().strip("'" ).strip('"')
        return clean_val.lower() in context.lower()

    def evaluate_move(self, action_type: str, target: str, manager_rationale: str, valid_files: Optional[List[str]] = None, active_pages: Optional[List[str]] = None, decision_history: List[dict] = [], current_artifacts: List[Any] = [], active_context: str = "") -> dict:
        """
        The Amnesic Policy Engine: Strictly enforces State and Safety.
        """
        
        # --- LAYER -4: SEMANTIC HYGIENE ---
        if action_type == "save_artifact":
             # Reject if target contains whitespace or looks like prose
             if " " in target.strip() or len(target) > 64:
                  return {
                      "auditor_verdict": "REJECT",
                      "confidence_score": 1.0,
                      "rationale": f"SEMANTIC POLLUTION: '{target}' is not a valid symbolic identifier. Use a single word or SNAKE_CASE.",
                      "correction": "Retry save_artifact with a clean identifier (e.g. RESULT or DATA_X)."
                  }

        # --- LAYER -3: IDEMPOTENCY & SEMANTIC BRIDGING (Primary State Logic) ---
        if action_type == "save_artifact":
            existing_art = next((a for a in current_artifacts if a.identifier == target), None)
            if existing_art:
                # 1. IDEMPOTENCY: If they are saving exactly what they already have, let it pass (Avoid Loop)
                if existing_art.summary in manager_rationale or target in manager_rationale:
                    return {
                        "auditor_verdict": "PASS",
                        "confidence_score": 1.0,
                        "rationale": f"Idempotent Save: You already have '{target}' in your Backpack. Proceeding."
                    }

                # 2. SEMANTIC BRIDGING: Allow grounded correction
                new_value_match = re.search(r'\b\d+\b', manager_rationale)
                new_value = new_value_match.group(0) if new_value_match else ""
                
                if self._check_grounding(new_value, active_context):
                    return {
                        "auditor_verdict": "PASS",
                        "confidence_score": 0.8,
                        "rationale": f"Semantic Bridging: Overwriting '{target}' with new evidence ({new_value})."
                    }
                
                return {
                    "auditor_verdict": "PASS", # FORGIVENESS: Just let it pass to break loops
                    "confidence_score": 0.5,
                    "rationale": "Forced artifact update to prevent state deadlock."
                }

        # --- LAYER -2.5: HALT VALIDATION ---
        if action_type == "halt_and_ask":
            # 1. Artifact Count/Named Check
            # Check for numeric count (e.g. "10 parts")
            # Improved regex to handle various wordings
            count_match = re.search(r'(\d+)[\s-]*(?:word|part|file|artifact|step)', self.goal.lower())
            if count_match:
                required_count = int(count_match.group(1))
                
                # Filter current_artifacts to only count those that seem relevant to the mission
                # (e.g. if the mission mentions PART_N, only count those)
                relevant_arts = current_artifacts
                if "PART_" in self.goal:
                    relevant_arts = [a for a in current_artifacts if "PART_" in str(a.identifier).upper()]
                
                if len(relevant_arts) < required_count:
                    return {
                        "auditor_verdict": "REJECT",
                        "confidence_score": 1.0,
                        "rationale": f"PREMATURE HALT: You claimed the mission is complete, but you only have {len(relevant_arts)}/{required_count} required parts saved as artifacts. You MUST save the data from the current file BEFORE halting.",
                        "correction": f"Save the data from your current Active Context as an artifact (e.g. PART_{len(relevant_arts)})."
                    }
            
            # Check for named artifacts explicitly mentioned in MISSION
            # e.g. "Save ... as an Artifact named 'modern_payroll.py'"
            named_art_matches = re.findall(r"artifact named ['\"]([^'\"]+)['\"]", self.goal.lower())
            for named_art in named_art_matches:
                if not any(a.identifier.lower() == named_art.lower() for a in current_artifacts):
                    return {
                        "auditor_verdict": "REJECT",
                        "confidence_score": 1.0,
                        "rationale": f"PREMATURE HALT: Missing required artifact '{named_art}' explicitly requested in mission.",
                        "correction": f"Save your result as '{named_art}' before halting."
                    }
            
            # 2. Reality Check (Numerical consistency)
            full_truth = active_context + " " + " ".join([f"{a.identifier}: {a.summary}" for a in current_artifacts])
            if not self._check_numerical_accuracy(target + " " + manager_rationale, full_truth):
                 return {
                    "auditor_verdict": "REJECT",
                    "confidence_score": 1.0,
                    "rationale": "FINAL REPORT HALLUCINATION: Your conclusion contains numbers that do not match the evidence in your Backpack or L1.",
                    "correction": "Re-examine your artifacts and the last file you read."
                }

        # --- LAYER 0: INFRASTRUCTURE STABILITY ---
        if action_type == "stage_context":
            # 1. Existence Check
            if valid_files is not None:
                # valid_files is list of paths
                basename = os.path.basename(target)
                exists = any(os.path.basename(f) == basename for f in valid_files)
                if not exists:
                    return {
                        "auditor_verdict": "REJECT",
                        "confidence_score": 1.0,
                        "rationale": f"FILE NOT FOUND: '{target}' does not exist in the environment.",
                        "correction": "Check the available files in your substrate map."
                    }

            # 2. Memory Limit Check
            user_files = [p for p in (active_pages or []) if "SYS:" not in p]
            # STRICT AMNESIA: Only one user file at a time unless ELASTIC mode is enabled
            if user_files and not self.elastic_mode and "ELASTIC" not in self.goal.upper():
                 return {
                     "auditor_verdict": "REJECT", 
                     "confidence_score": 1.0, 
                     "rationale": f"L1 RAM VIOLATION: Memory is full ({user_files[0]} is open). Use 'unstage_context' first."
                 }

        if action_type == "unstage_context":
            if not active_pages:
                 return {"auditor_verdict": "REJECT", "confidence_score": 1.0, "rationale": "Context is already empty."}
            if "SYS:" in target:
                 return {"auditor_verdict": "REJECT", "confidence_score": 1.0, "rationale": "SYSTEM_PAGE_PROTECTION: Mission/Strategy is permanent."}
            
            # Verify target is actually staged
            clean_target = target.replace("FILE:", "").strip()
            # Handle list of pages which might have FILE: prefix
            active_clean = [p.replace("FILE:", "").strip() for p in active_pages]
            if clean_target not in active_clean:
                 return {
                     "auditor_verdict": "REJECT", 
                     "confidence_score": 1.0, 
                     "rationale": f"STALEMATE: File '{clean_target}' is NOT in L1. It may have already been unstaged. Move to next step."
                 }

        # --- LAYER 1: PHYSICAL VALIDATION (Reality Anchoring) ---
        if action_type == "verify_step":
            # Allow if data is in the Backpack (Persistent memory)
            target_lower = target.lower()
            grounded_in_backpack = any(a.identifier.lower() in target_lower or a.summary.lower() in target_lower for a in current_artifacts)
            if grounded_in_backpack:
                return {"auditor_verdict": "PASS", "confidence_score": 1.0, "rationale": "Grounded in persistent artifacts."}
            
            # Allow if data is in Active Context (L1)
            if active_context and not self._check_numerical_accuracy(manager_rationale, active_context):
                return {"auditor_verdict": "REJECT", "confidence_score": 1.0, "rationale": "VERIFICATION HALLUCINATION: Reality contradicts your numbers."}

        # --- LAYER 1.5: ANTI-HALLUCINATION ---
        if action_type in ["save_artifact", "edit_file"]:
            user_files = [p for p in (active_pages or []) if "SYS:" not in p]
            if not user_files and not (action_type == "save_artifact" and not valid_files):
                return {
                    "auditor_verdict": "REJECT",
                    "confidence_score": 1.0,
                    "rationale": f"L1 EMPTY: You cannot {action_type} without an open user file."
                }

        # --- LAYER 1.8: ANTI-AMNESIA (Save-Then-Close) ---
        if action_type == "unstage_context":
            lower_rationale = manager_rationale.lower()
            target_clean = target.replace("FILE:", "").strip()
            
            # Generic State Check: Did we save a new artifact since staging this file?
            staged_turn = -1
            for h in reversed(decision_history):
                if h.get('tool_call') == "stage_context" and target_clean in str(h.get('target', '')) and h.get('auditor_verdict') == "PASS":
                    staged_turn = h.get('turn', 0)
                    break
            
            saves_since = 0
            if staged_turn != -1:
                for h in decision_history:
                    if h.get('turn', 0) >= staged_turn and h.get('tool_call') == "save_artifact" and h.get('auditor_verdict') == "PASS":
                        saves_since += 1

            if any(kw in lower_rationale for kw in ["extracted", "found", "value is", "saved", "retrieved", "stored", "recorded"]):
                # Allow if a new save happened since staging
                if saves_since > 0:
                    return {"auditor_verdict": "PASS", "confidence_score": 1.0, "rationale": "Data saved since staging."}
                
                # ALSO allow if the mentioned data is already in artifacts (Persistent memory)
                artifact_mentioned = any(a.identifier.lower() in lower_rationale for a in current_artifacts)
                if artifact_mentioned:
                    return {"auditor_verdict": "PASS", "confidence_score": 1.0, "rationale": "Artifact already in backpack. Safe to unstage."}

                if saves_since == 0:
                     return {
                        "auditor_verdict": "REJECT",
                        "confidence_score": 1.0,
                        "rationale": f"AMNESIA RISK: You claim to have data from {target_clean} but saved 0 artifacts. Save FIRST."
                    }

            # Explicit Dismissal bypass
            if any(kw in lower_rationale for kw in ["useless", "noise", "making room", "done with"]):
                return {"auditor_verdict": "PASS", "confidence_score": 1.0, "rationale": "Explicit dismissal accepted."}

        # --- LAYER -2: LOOP MANAGEMENT ---
        if decision_history:
            last_move = decision_history[-1]
            last_tool = last_move.get('tool_call', '').split(' ')[0] if 'tool_call' in last_move else last_move.get('move', {}).get('tool_call')
            last_target = str(last_move.get('target', ''))
            last_verdict = last_move.get('auditor_verdict')
            last_exec = last_move.get('execution_result', 'UNKNOWN')

            # Stalemate detection (Identical consecutive moves that ALREADY SUCCEEDED)
            if last_tool == action_type and last_target == target:
                if last_verdict == "PASS" and last_exec != "FAILED_EXECUTION":
                    # Exempt cumulative tools that might legitimately be called multiple times
                    if action_type not in ["calculate", "write_file", "verify_step"]:
                        return {
                            "auditor_verdict": "REJECT", 
                            "confidence_score": 1.0, 
                            "rationale": f"STALEMATE: You already successfully performed {action_type}({target}). Move to the next step in your plan."
                        }

            # Recursive loop check (Last 3 turns)
            repeats = 0
            for h in decision_history[-3:]:
                if h.get('tool_call') == action_type and str(h.get('target')) == target: repeats += 1
            
            # Exemptions from loop detection
            is_exempt = action_type in ["stage_context", "unstage_context", "edit_file", "write_file"]
            if action_type == "save_artifact":
                # Only exempt if it hasn't actually succeeded yet (to allow retries after hallucination rejections)
                has_succeeded = any(h.get('tool_call') == action_type and str(h.get('target')) == target and h.get('auditor_verdict') == "PASS" for h in decision_history)
                if not has_succeeded:
                    is_exempt = True

            if repeats >= 2 and not is_exempt:
                return {
                    "auditor_verdict": "REJECT", "confidence_score": 1.0,
                    "rationale": f"LOOP DETECTED: You've tried {action_type} on {target} repeatedly. Try something else."
                }

        # --- LAYER 2: RELEVANCE & SECURITY ---
        if self._check_hard_constraints(action_type, target):
             return {"auditor_verdict": "REJECT", "confidence_score": 1.0, "rationale": "Policy Violation."}

        relevance_score = self._check_relevance(action_type, target, manager_rationale)
        threshold = 0.15 if action_type in ["save_artifact", "unstage_context", "calculate"] else 0.25
        
        if relevance_score < threshold: 
            return {"auditor_verdict": "REJECT", "confidence_score": 1.0, "rationale": f"Irrelevant action ({relevance_score:.2f})."}

        # --- LAYER 3: LLM JUDGE ---
        try:
            verdict = self._run_llm_audit(action_type, target, manager_rationale, relevance_score, active_pages)
            return {
                "auditor_verdict": verdict.outcome,
                "confidence_score": 0.9 if verdict.outcome == "PASS" else 0.5,
                "rationale": verdict.rationale,
                "correction": verdict.correction
            }
        except Exception as e:
            logger.warning(f"LLM Audit failed: {e}. Falling back to heuristic.")
            # HEURISTIC FALLBACK: If it's a read-only action and not clearly dangerous, let it pass to avoid blocking.
            if action_type in ["stage_context", "unstage_context", "verify_step", "calculate"]:
                return {
                    "auditor_verdict": "PASS",
                    "confidence_score": 0.3,
                    "rationale": "Heuristic Pass: Action is low-risk and LLM failed to judge.",
                    "correction": None
                }
            
            # For writes/edits, be safer and reject
            return {
                "auditor_verdict": "REJECT",
                "confidence_score": 0.3,
                "rationale": "Heuristic Reject: Action is higher-risk and LLM failed to judge.",
                "correction": "Try a simpler, safer move."
            }

    def _check_hard_constraints(self, action: str, target: str) -> bool:
        forbidden = ["DELETE", "DROP", "TRUNCATE", ".env", "api_key"]
        for word in forbidden:
            if word in target.upper() or word in action.upper(): return True
        return False

    def _check_relevance(self, action: str, target: str, rationale: str = "") -> float:
        action_text = f"{action} {target}. Rationale: {rationale}"
        action_vector = list(self.embedder.embed([action_text]))[0]
        return float(np.dot(self.goal_vector, action_vector))

    def _run_llm_audit(self, action: str, target: str, rationale: str, rel_score: float, active_pages: Optional[List[str]]) -> AuditorVerdict:
        system_prompt = AUDITOR_SYSTEM_PROMPT.format(goal=self.goal, constraints=self.constraints)
        loaded_files = ", ".join(active_pages) if active_pages else "None"
        
        # Truncate target to prevent distraction by large code blocks
        display_target = target[:500] + "... [TRUNCATED]" if len(target) > 500 else target
        
        user_prompt = f"L1: {loaded_files}\nAction: {action}\nTarget: {display_target}\nRationale: {rationale}\nVerdict?"
        return self.driver.generate_structured(user_prompt=user_prompt, schema=AuditorVerdict, system_prompt=system_prompt)

# --- LangGraph Node Wrapper ---
_shared_driver = OllamaDriver() 

def node_auditor(state):
    goal = state.get('mission_statement', "UNKNOWN")
    constraints = state.get('constraints', [])
    fw_state = state.get('framework_state')
    elastic_mode = getattr(fw_state, 'elastic_mode', False) if fw_state else False
    auditor = Auditor(goal=goal, constraints=constraints, driver=_shared_driver, elastic_mode=elastic_mode)
    
    pending_move = state.get('manager_decision', {})
    tool_call = pending_move.get('tool_call', 'None')
    target = pending_move.get('target', 'None')
    rationale = pending_move.get('thought_process', pending_move.get('rationale', 'None'))
    
    raw_map = state.get('active_file_map', {})
    valid_files = list(raw_map.keys()) if isinstance(raw_map, dict) else []
    active_pages = [] # Note: Pager object preferred for real checks

    result = auditor.evaluate_move(
        action_type=tool_call, target=target, manager_rationale=rationale,
        valid_files=valid_files, active_pages=active_pages,
        decision_history=state.get('decision_history', []),
        current_artifacts=state.get('framework_state', MagicMock()).artifacts,
        active_context=state.get('current_context_window', "")
    )
    
    trace = {
        "step": len(state.get("decision_history", [])),
        "tool_call": f"{tool_call} {target}",
        "rationale": rationale,
        "auditor_verdict": result["auditor_verdict"],
        "confidence_score": result["confidence_score"]
    }
    if result["auditor_verdict"] != "PASS" and result.get("correction"):
        trace["rationale"] += f" [AUDITOR CORRECTION: {result['correction']}]"

    return {
        "decision_history": state.get("decision_history", []) + [trace],
        "global_uncertainty": state.get("global_uncertainty", 0.0) + (0.15 if result["auditor_verdict"] != "PASS" else 0.0)
    }
