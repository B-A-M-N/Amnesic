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
        - **ARTIFACT PRIORITY**: If you read a value, SAVE IT immediately. Do not switch files until the data is secured.
        - **STRATEGY CHECK**: If you are ALREADY in the target strategy (e.g., IMPLEMENTER), DO NOT switch to it again.
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
        # SAFEGUARD: Filter Nones
        safe_artifacts = [a for a in state.artifacts if a]
        if safe_artifacts:
            checklist = "\n        [COMPLETED ARTIFACTS CHECKLIST]\n"
            for a in safe_artifacts:
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

        # 3. GPS: Calculate the next sequential step
        gps_hint = ""
        current_count = len([a for a in safe_artifacts if a.identifier not in ["TOTAL", "VERIFICATION", "FILE_LIST"]])
        
        # Heuristic for Marathon/Overflow
        if "step_" in state.task_intent or any("step_" in a.identifier for a in safe_artifacts):
             gps_hint = f"\n        [GPS GUIDANCE] You have {current_count} parts. NEXT TARGET: 'step_{current_count}.txt'."
        elif "log_" in state.task_intent or any("log_" in a.identifier for a in safe_artifacts):
             gps_hint = f"\n        [GPS GUIDANCE] You have {current_count} values. NEXT TARGET: 'overflow_data/log_{current_count:02d}.txt'."

        # Format artifacts for prompt: IDENTIFIERS ONLY (Artifact Shadowing)
        # REMOVED BRACKETS: 8B models confused by <id>. Using raw ID.
        found_artifacts = [f"{a.identifier}" for a in safe_artifacts]
        artifacts_summary = ", ".join(found_artifacts) if found_artifacts else "None"

        return f"""
        [MISSION PROGRESS]
        {state.task_intent}
        [CURRENT STRATEGY]: {state.strategy}
        {checklist}
        {gps_hint}
        {progress_block}
        
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