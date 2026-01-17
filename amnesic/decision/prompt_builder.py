import logging
import re
from typing import List, Dict, Any, Optional
from ..presets.code_agent import FrameworkState

logger = logging.getLogger("amnesic.prompt")

class ManagerPromptBuilder:
    @staticmethod
    def build_system_prompt(state: FrameworkState, l1_files: Any, artifacts_summary: str, amnesia_rule: str, feedback_alert: str, **kwargs) -> str:
        from ..presets.code_agent import MANAGER_SYSTEM_PROMPT
        # We handle kwargs to be robust against session.py changes
        return MANAGER_SYSTEM_PROMPT.format(
            l1_files=str(l1_files),
            artifacts=artifacts_summary,
            amnesic_sequence="DUMMY_SEQ",
            amnesia_rule=amnesia_rule,
            state_dump=str(state.model_dump()),
            feedback=feedback_alert
        )

    @staticmethod
    def build_user_prompt(
        state: FrameworkState,
        artifacts_summary: str,
        l1_files: List[str],
        l1_warning: str,
        feedback_alert: str,
        map_summary: str,
        history_block: str,
        active_content: str,
        forbidden_tools: List[str] = []
    ) -> str:
        # Determine rules based on elastic mode
        elastic_mode = getattr(state, 'elastic_mode', False)
        
        if elastic_mode:
            amnesia_rule = "- **ELASTIC CONTEXT**: You may have MULTIPLE user files open simultaneously as long as they fit in L1 RAM."
        else:
            amnesia_rule = "- **ONE-FILE LIMIT**: You may only have ONE user file open at a time. You MUST 'unstage_context' before opening another."

        standard_instructions = f"""
        {amnesia_rule}
        - **HIGH-SPEED FLOW**: You MUST use the 'Stage -> Save -> Stage' pattern. 
        - **NO UNSTAGE**: DO NOT use 'unstage_context'. The system EVICTS old files automatically when you stage a new one. Manual unstaging is a waste of a turn.
        - **PINNED PAGES**: Pages marked as (PINNED) are critical and CANNOT be unstaged.
        - **SEMANTIC PINNING**: Use 'PINNED_L1:ID: value' to keep critical logic in L1.
        - **CONTEXTUAL GREPPING**: For large files, use 'stage_context(file.py?query=symbol_name)'.
        - **ARTIFACT SHADOWING**: You only see pointers <id>. Use 'stage_artifact(id)' to read them.
        - **ONE MOVE**: State the single next logical action.
        """
        
        snapshot_warning = """
        [!!! CRITICAL: RESTRICTED REASONING MODE !!!]
        YOU ARE IN SNAPSHOT MODE. 
        - DISK ACCESS IS PHYSICALLY BLOCKED.
        - THE ENVIRONMENT IS EMPTY.
        - YOU MUST ANSWER USING ONLY THE ARTIFACTS IN 'THE BACKPACK'.
        - DO NOT ATTEMPT TO 'stage_context'.
        """
        # MODE SELECTION: If stage_context is forbidden, we are in Snapshot/Post-Mortem mode.
        is_restricted = "stage_context" in forbidden_tools
        
        # 1. ARTIFACT CHECKLIST: Make it very clear what is already done.
        checklist = ""
        if state.artifacts:
            checklist = "\n        [COMPLETED ARTIFACTS CHECKLIST]\n"
            for a in state.artifacts:
                checklist += f"        - {a.identifier} [DONE]\n"

        # 2. PROGRESS POINTERS: "You are here"
        progress_block = ""
        if state.plan:
            current_idx = state.current_step_id
            progress_block = "\n        [STATE TRANSITION STATUS]\n"
            for i, step in enumerate(state.plan):
                if i < current_idx:
                    status = "[SEALED - ACCESS DENIED]"
                    pointer = ""
                elif i == current_idx:
                    status = "[ACTIVE]"
                    pointer = " *YOU ARE HERE*"
                else:
                    status = "[LOCKED]"
                    pointer = ""
                progress_block += f"        Step {i}: {step.description} {status}{pointer}\n"
            
            if current_idx < len(state.plan) - 1:
                progress_block += f"        NEXT STATE GATE -> {state.plan[current_idx + 1].description}\n"

        # Format artifacts for prompt: IDENTIFIERS ONLY (Artifact Shadowing)
        found_artifacts = [f"<{a.identifier}>" for a in state.artifacts]
        artifacts_summary = ", ".join(found_artifacts) if found_artifacts else "None"

        return f"""
        [MISSION PROGRESS]
        {state.task_intent}
        {checklist}
        {progress_block}
        
        [STATE DELTA GOVERNANCE]
        - YOUR REASONING IS EPHEMERAL: It is wiped every turn. Only 'Backpack' artifacts persist.
        - SEALED PAST: Steps marked [SEALED] cannot be revisited or re-justified.
        - NO DELTA = FAILURE: If your next move does not change the Backpack or L1 RAM, it is a wasted cycle.
        
        [CRITICAL GROUND TRUTH (The Backpack)]
        You currently hold pointers to the following Artifacts: {artifacts_summary}
        Your Active L1 RAM contains: {l1_files}
        
        {l1_warning}
        {feedback_alert}
        
        ### OPERATIONAL INSTRUCTIONS ###
        {snapshot_warning if is_restricted else standard_instructions}
        - **ARTIFACT CONTENT**: You only see 'Pointers' <id> to artifacts. 
        - Use 'stage_artifact(id)' to read full content into L1.
        - Use 'calculate(SUM_BACKPACK)' to aggregate numerical artifacts.

        [ENVIRONMENT STRUCTURE - DISK MAP]
        {map_summary if (map_summary and not is_restricted) else "[ENVIRONMENT ACCESS DISABLED]"}
        !!! IMPORTANT !!!: The list above is the ABSOLUTE TRUTH of the file system. 

        {history_block}
        
        [CURRENT L1 CONTEXT CONTENT]
        {active_content}

        [GOVERNANCE RULES]
        1. FORWARD ONLY: Once an artifact (e.g. PART_0) is in the checklist, DO NOT stage its source file ever again.
        2. SEQUENTIAL FLOW: Open the NEXT numerical file that is not yet completed.
        3. AUTO-EVICTION: Never use 'unstage_context'. Just 'stage_context' the NEXT file immediately after saving your artifact. The system handles eviction.
        4. IMMEDIATE SAVE: If a file is in 'Active L1 RAM', your VERY NEXT move MUST be 'save_artifact'.
        5. PERSONA TRANSITION: If strategy is 'Architect' and you saved a PLAN, you MUST 'switch_strategy' to 'Implementer'.
        6. STATE DELTA: Your goal is to move a file to L1, or a fact to the Backpack. 
        7. HALT: If all steps are complete, use 'halt_and_ask'.
        8. PRE-CALCULATION: Before using 'calculate', ensure all required numbers are saved as Artifacts.
        9. COUNT CHECK: If mission specifies a count (e.g. 10 items), COUNT your artifacts. If you have fewer, do NOT halt.

        RESPONSE MUST BE VALID JSON.
        
        [TOOL SYNTAX REMINDER]
        - **target** field: MUST be a single symbolic name (e.g. RESULT_1).
        - To save a value: {{"tool_call": "save_artifact", "target": "ID_NAME: the actual value content"}}
        - To pin logic in L1: {{"tool_call": "save_artifact", "target": "PINNED_L1:ID_NAME: the actual value content"}}
        - To stage a specific symbol: {{"tool_call": "stage_context", "target": "path/to/file.py?query=function_name"}}
        - To write a file: {{"tool_call": "write_file", "target": "path/to/file.ext: THE FULL FILE CONTENT HERE"}}
        - **UNSTAGE**: You MUST 'unstage_context' before opening a new file unless in ELASTIC mode.
        """


    @staticmethod
    def format_map_summary(file_map: List[Dict[str, Any]]) -> str:
        map_lines = []
        for f in file_map:
            path = f.get('path', 'unknown')
            classes = [c['name'] for c in f.get('classes', [])]
            funcs = [func['name'] for func in f.get('functions', [])]
            line = f"- {path}"
            if classes: line += f" [Classes: {', '.join(classes)} ]"
            if funcs: line += f" [Funcs: {', '.join(funcs)} ]"
            map_lines.append(line)
        return "\n".join(map_lines)[:2500]