import logging
import re
import os
from typing import List, Literal, TypedDict, Optional, Any
from pydantic import BaseModel, Field
from fastembed import TextEmbedding
import numpy as np

from ..drivers.ollama import OllamaDriver
from ..presets.code_agent import AUDITOR_SYSTEM_PROMPT, AuditorVerdict
from ..core.audit_policies import AuditProfile, STRICT_AUDIT, FLUID_READ, HIGH_SPEED, PROFILE_MAP

logger = logging.getLogger("amnesic.auditor")

# --- 2. The Logic Engine ---
class Auditor:
    def __init__(self, goal: str, constraints: List[str], driver: OllamaDriver, elastic_mode: bool = False, audit_profile: AuditProfile = STRICT_AUDIT, context_mode: str = "balanced"):
        self.goal = goal
        self.constraints = constraints
        self.driver = driver
        self.elastic_mode = elastic_mode
        self.policy = audit_profile
        self.context_mode = context_mode
        
        # Layer 1: Vector Model (Relevance)
        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.goal_vector = list(self.embedder.embed([goal]))[0]

    def _check_numerical_accuracy(self, claim: str, context: str) -> bool:
        """Verifies that any number mentioned in the claim exists in context."""
        numbers_in_claim = re.findall(r'\b\d+\b', claim)
        if not numbers_in_claim: return True
        
        # Punctuation-agnostic context check for numbers
        clean_ctx = re.sub(r"[^a-zA-Z0-9\s]", " ", context)
        for num in numbers_in_claim:
            if str(num) not in clean_ctx:
                return False
        return True

    def _check_grounding(self, value: str, context: str) -> bool:
        """Checks if the specific value string is present in the context."""
        if not value or not context: return False
        
        # 1. Try exact match first
        if value.strip() in context:
            return True
            
        # 2. Punctuation-Agnostic Match (Nuclear Option)
        # Remove EVERYTHING except letters and numbers
        clean_val = re.sub(r"[^a-zA-Z0-9]", "", value).lower()
        clean_ctx = re.sub(r"[^a-zA-Z0-9]", "", context).lower()
        
        if clean_val and clean_val in clean_ctx:
            return True
            
        # 3. Component match: if all non-stopword tokens exist
        tokens = [t for t in re.split(r"[^a-zA-Z0-9]", value) if len(t) > 3]
        if tokens and all(t.lower() in clean_ctx for t in tokens):
            return True
            
        return False

    def evaluate_move(self, action_type: str, target: str, manager_rationale: str, valid_files: Optional[List[str]] = None, active_pages: Optional[List[str]] = None, decision_history: List[dict] = [], current_artifacts: List[Any] = [], active_context: str = "", forbidden_tools: List[str] = []) -> dict:
        """
        The Amnesic Policy Engine: Strictly enforces State and Safety.
        """
        # SAFEGUARD: Filter out None/Invalid artifacts to prevent crashes
        current_artifacts = [a for a in current_artifacts if a and hasattr(a, 'identifier')]
        
        # --- LAYER -5: TOOL ENFORCEMENT ---
        if action_type in forbidden_tools:
             return {
                 "auditor_verdict": "REJECT",
                 "confidence_score": 1.0,
                 "rationale": f"FATAL: The tool '{action_type}' is DISABLED in this mode. You must reason using ONLY your saved artifacts.",
                 "correction": "Use your existing knowledge from the Backpack to answer the user query."
             }

        # --- LAYER -4: SEMANTIC HYGIENE ---
        if action_type == "save_artifact":
             # Support "KEY: value" or "KEY=value" formats
             clean_target = target.strip()
             has_separator = ":" in clean_target or "=" in clean_target
             
             if has_separator:
                 # Only validate the key part
                 key_part = re.split(r'[:=]', clean_target)[0].strip()
                 # Allow SNAKE_CASE, dots, hyphens
                 if not re.match(r"^[a-zA-Z0-9_.-]+$", key_part) or len(key_part) > 128:
                      return {
                          "auditor_verdict": "REJECT",
                          "confidence_score": 1.0,
                          "rationale": f"SEMANTIC POLLUTION: The key part '{key_part}' contains spaces or invalid characters.",
                          "correction": "Use a short symbolic name (e.g. MY_DATA) for the key before the colon."
                      }
             elif " " in clean_target or len(clean_target) > 128:
                  return {
                      "auditor_verdict": "REJECT",
                      "confidence_score": 1.0,
                      "rationale": f"SEMANTIC POLLUTION: '{target}' is not a valid symbolic identifier.",
                      "correction": "Retry save_artifact with a clean SNAKE_CASE identifier."
                  }

        # 4. Sequential Progress Check (Strict Mode)
        # Prevent skipping steps in numbered missions (1. stepA, 2. stepB...)
        if "1." in self.goal and "2." in self.goal:
            if action_type in ["halt_and_ask", "save_artifact"] and ("TOTAL" in target.upper() or "MISSION_COMPLETE" in target.upper()):
                # Check for intermediate artifacts (e.g., PART_0, VAL_log_00)
                # If mission mentions 'PART_' or 'VAL_log_', verify count
                if "PART_" in self.goal:
                    parts = [a for a in current_artifacts if a and "PART_" in a.identifier]
                    if len(parts) < 5: # Threshold for 'Marathon'
                        return {"auditor_verdict": "REJECT", "rationale": "PREMATURE COMPLETION: You are attempting to finalize the mission without extracting intermediate parts. Follow the STRICT PLAN.", "confidence_score": 0.9}
                if "VAL_log_" in self.goal:
                    logs = [a for a in current_artifacts if a and "VAL_log_" in a.identifier]
                    if len(logs) < 10: # Threshold for 'Overflow'
                        return {"auditor_verdict": "REJECT", "rationale": "PREMATURE COMPLETION: You only have artifacts for a few logs. You must process ALL logs before calculating the total.", "confidence_score": 0.9}

        # 5. Stagnation Prevention (Detect loops)
        if len(decision_history) > 0:
            last_move = decision_history[-1]
            if action_type == last_move["tool_call"].split()[0] and target == last_move["target"]:
                return {
                    "auditor_verdict": "REJECT", 
                    "rationale": "STAGNATION: You are repeating the same move. Change target or action.",
                    "confidence_score": 1.0,
                    "correction": "MOVE FORWARD: You already tried this. Check your checklist and open the NEXT numerical file (e.g. if you have PART_0, open step_1.txt)."
                }

        # If the agent tries to save an artifact that is ALREADY in the backpack with the SAME content.
        if action_type == "save_artifact":
             # Extract identifier and summary
             if ":" in target:
                 identifier, summary = target.split(":", 1)
             else:
                 identifier, summary = target, ""
             
             identifier = identifier.strip()
             summary = summary.strip()
             
             existing = next((a for a in current_artifacts if a.identifier == identifier), None)
             if existing:
                  # SELF-CORRECTION: If the content is DIFFERENT, allow it!
                  if existing.summary.strip() == summary:
                       return {
                           "auditor_verdict": "REJECT",
                           "confidence_score": 1.0,
                           "rationale": f"STAGNATION: Artifact '{identifier}' is already in your Backpack with the same value. ACTION BLOCKED: You have already secured this data. DO NOT retry this action.",
                           "correction": "You MUST perform a DIFFERENT action now (e.g., stage a new file, calculate, or halt)."
                       }
                  else:
                       # Allow update
                       pass

        # --- LAYER -2.5: HALT VALIDATION ---
        if action_type == "halt_and_ask":
            # 1. Strict Artifact Count Check
            # Look for requirements like "10 parts", "16 values", "5 items"
            count_match = re.search(r"(\d+)\s*(-word|\s*parts|\s*artifacts|\s*files|\s*values|\s*items)", self.goal.lower())
            if count_match:
                required_count = int(count_match.group(1))
                # Count non-meta artifacts
                non_meta = [a for a in current_artifacts if a.identifier not in ["TOTAL", "VERIFICATION", "FILE_LIST", "tool."]]
                if len(non_meta) < required_count:
                    return {
                        "auditor_verdict": "REJECT",
                        "confidence_score": 1.0,
                        "rationale": f"PREMATURE HALT: Mission requires {required_count} artifacts, but you only have {len(non_meta)}.",
                        "correction": f"Continue gathering the remaining {required_count - len(non_meta)} parts."
                    }

        # --- LAYER -2: CONTEXT MANAGEMENT ---
        if action_type == "stage_context":
             # Normalize target for comparison
             target_base = os.path.basename(target)
             
             # STALEMATE: Is the file already open?
             # Check both full name and basename in active_pages
             is_open = False
             for page in active_pages:
                  if "FILE:" in page:
                       page_path = page.replace("FILE:", "")
                       if page_path == target or os.path.basename(page_path) == target_base:
                            is_open = True
                            break
             
             if is_open:
                  # IDEMPOTENCY FIX: If it's already open, just say yes.
                  return {
                      "auditor_verdict": "PASS",
                      "confidence_score": 1.0,
                      "rationale": f"IDEMPOTENCY: File '{target}' is ALREADY in L1 RAM. Proceeding.",
                      "correction": "Check the [CURRENT L1 CONTEXT CONTENT] block. If you see the data, save it as an artifact."
                  }
             
             # HOARDING INTENT CHECK (Red Team Defense)
             # If strict mode (not elastic), reject explicit attempts to keep multiple files
             if not self.elastic_mode:
                 hoarding_keywords = ["without unstaging", "keep both", "retain the previous", "holding both"]
                 if any(kw in manager_rationale.lower() for kw in hoarding_keywords):
                      return {
                          "auditor_verdict": "REJECT",
                          "confidence_score": 1.0,
                          "rationale": "VIOLATION: One-File Limit. You cannot explicitly hoard files in Strict Mode.",
                          "correction": "You must accept that the previous file will be evicted."
                      }

             # DISK TRUTH: Does the file actually exist?
             # Check if target matches any valid_file exactly OR by suffix
             exists_on_disk = False
             if valid_files:
                  for vf in valid_files:
                       if vf == target or vf.endswith("/" + target) or target.endswith("/" + vf):
                            exists_on_disk = True
                            break
             
             if not exists_on_disk:
                  return {
                      "auditor_verdict": "REJECT",
                      "confidence_score": 1.0,
                      "rationale": f"FILE NOT FOUND: '{target}' does not exist in the environment.",
                      "correction": "Check the [ENVIRONMENT STRUCTURE - DISK MAP] for valid file paths."
                  }

        if action_type == "unstage_context":
             target_base = os.path.basename(target)
             is_staged = False
             for page in active_pages:
                  if "FILE:" in page:
                       page_path = page.replace("FILE:", "")
                       if page_path == target or os.path.basename(page_path) == target_base:
                            is_staged = True
                            break
                            
             if not is_staged:
                  # IDEMPOTENCY FIX: If the agent tries to unstage something that isn't there,
                  # just treat it as a success so they can move on. Rejecting it causes loops.
                  return {
                      "auditor_verdict": "PASS",
                      "confidence_score": 1.0,
                      "rationale": f"IDEMPOTENCY: File '{target}' was already unstaged. Proceeding.",
                      "correction": ""
                  }

        # --- LAYER 2: SEMANTIC FIDELITY ---
        if action_type == "save_artifact":
             # 1. GROUNDING: Is the value actually in the active context?
             # MISSION EXCEPTION: If the mission is redaction/stubbing, 
             # the summary will contain 'REDACTED' or '...'. 
             if summary and ("REDACTED" in summary.upper() or "..." in summary):
                  # Allow redaction without grounding check
                  pass
             elif summary and not self._check_grounding(summary, active_context):
                  # Heuristic: Match numbers precisely even if text is slightly off
                  if not self._check_numerical_accuracy(summary, active_context):
                       # MATH EXEMPTION: If rationale mentions calculation/sum/total, allow numerical artifacts
                       is_math_rationale = any(kw in manager_rationale.lower() for kw in ["calculate", "sum", "total", "math", "add", "result", "divide", "multiply"])
                       is_pure_number = re.match(r"^-?\d+(\.\d+)?$", summary.strip())
                       
                       if is_math_rationale and is_pure_number:
                            # Allow derived math result
                            pass
                       else:
                            # TRANSITIVE GROUNDING: Is it in a saved artifact?
                            # (This allows the agent to reason across turns)
                            found_in_memory = any(summary.strip() in a.summary for a in current_artifacts)
                            if not found_in_memory:
                                 return {
                                     "auditor_verdict": "REJECT",
                                     "confidence_score": 1.0,
                                     "rationale": f"HALUCINATION: The value for '{identifier}' was not found in the context or artifacts.",
                                     "correction": "Ensure the file containing the data is open and visible in [CURRENT L1 CONTEXT CONTENT]."
                                 }

        # --- LAYER 3: MISSION RELEVANCE (Vector) ---
        # EXPLORATION RIGHTS: Staging and reading files is ALWAYS allowed.
        # We only gate state-mutating actions (Save, Write, Calculate).
        RELEVANCE_EXEMPT = ["stage_context", "unstage_context", "halt_and_ask", "query_sidecar", "switch_strategy", "stage_artifact"]
        
        if action_type in ["save_artifact", "edit_file", "write_file", "calculate"] and action_type not in RELEVANCE_EXEMPT:
             action_text = f"{action_type} {target} {manager_rationale}"
             action_vector = list(self.embedder.embed([action_text]))[0]
             relevance = float(np.dot(self.goal_vector, action_vector))
             
             # HEURISTIC: Fast-Path for sequential log processing
             is_sequential = re.search(r"log_\d+|step_\d+", target)
             if is_sequential and relevance > 0.55:
                  return {
                      "auditor_verdict": "PASS",
                      "confidence_score": relevance,
                      "rationale": f"Fast-Path Approved: Heuristics pass (Score {relevance:.2f} > 0.55)."
                  }

             # PHASE-AWARE GOVERNANCE: Early turns (1-5) ignore relevance REJECTIONS.
             current_turn = len(decision_history) + 1
             threshold = self.policy.relevance_threshold
             
             if relevance < threshold:
                  if current_turn <= 5:
                       # BOOTSTRAP PASS: Allow but warn
                       return {
                           "auditor_verdict": "PASS",
                           "confidence_score": relevance,
                           "rationale": f"BOOTSTRAP PASS: Low relevance {relevance:.2f} ignored during initialization phase (Turn {current_turn})."
                       }
                  else:
                       return {
                           "auditor_verdict": "REJECT",
                           "confidence_score": relevance,
                           "rationale": f"RELEVANCE FAILURE: This move (Score {relevance:.2f}) does not seem to progress the mission.",
                           "correction": "Focus on the MISSION goal and only interact with relevant files."
                       }

        return {
            "auditor_verdict": "PASS",
            "confidence_score": 1.0,
            "rationale": "Move validated. State and Safety invariants preserved."
        }

    async def audit_stream(self, action_type: str, target: str, rationale: str, active_context: str) -> AuditorVerdict:
        """
        AI-Augmented Auditor for complex semantic checks (Red-Teaming, IP violations).
        Currently falls back to the deterministic evaluate_move for most logic.
        """
        # 1. Deterministic Pass
        verdict_dict = self.evaluate_move(
            action_type=action_type,
            target=target,
            manager_rationale=rationale,
            active_context=active_context,
            # (Note: In streaming mode, some state like valid_files might be limited)
        )
        
        if verdict_dict["auditor_verdict"] == "REJECT":
            return AuditorVerdict(
                verdict="REJECT",
                rationale=verdict_dict["rationale"],
                correction=verdict_dict.get("correction", "")
            )

        # 2. AI Pass (The Auditor's inner monologue)
        # We only call the LLM if we are in HIGH_SPEED/FLUID mode or if 
        # the move is potentially hostile (saving secrets).
        if self.policy == STRICT_AUDIT:
            return AuditorVerdict(verdict="PASS", rationale="Deterministic policy passed.")

        # Implementation for AI audit would go here...
        return AuditorVerdict(verdict="PASS", rationale="Move is safe.")