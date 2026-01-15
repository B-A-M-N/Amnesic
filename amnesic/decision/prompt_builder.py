import json
from typing import List, Dict, Any, Optional
from ..presets.code_agent import MANAGER_SYSTEM_PROMPT, ManagerMove, FrameworkState

class ManagerPromptBuilder:
    @staticmethod
    def build_system_prompt(
        state: FrameworkState,
        l1_files: List[str],
        l2_files: List[str],
        artifacts_summary: str,
        feedback_alert: str,
        amnesia_rule: str,
        eviction_rule: str,
        forbidden_tools: List[str] = []
    ) -> str:
        state_dump = state.model_dump_json(indent=2)
        tools_list = ManagerMove.model_json_schema()['properties']['tool_call']['enum']
        
        # Filter tools for restricted mode
        if forbidden_tools:
            tools_list = [t for t in tools_list if t not in forbidden_tools]
        
        return MANAGER_SYSTEM_PROMPT.format(
            state_dump=state_dump, 
            tools_available=", ".join(tools_list),
            l1_files=l1_files,
            l2_files=l2_files,
            artifacts=artifacts_summary,
            feedback=feedback_alert,
            amnesia_rule=amnesia_rule,
            eviction_rule=eviction_rule
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
        standard_instructions = """
        - **ONE-FILE LIMIT**: You may only have ONE user file open at a time.
        - **PINNED PAGES**: Pages marked as (PINNED) are critical system state and do NOT count towards the One-File Limit. They CANNOT be unstaged.
        - **NEVER** re-read or re-save data for artifacts you already have in 'The Backpack'.
        - **TRUST** the artifacts above as your only long-term memory.
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
        # We must NOT show the environment map to prevent the model from 'reaching' for disk.
        is_restricted = "stage_context" in forbidden_tools
        
        map_block = map_summary if (map_summary and not is_restricted) else "[ENVIRONMENT ACCESS DISABLED - REASON FROM MEMORY ONLY]"
        
        chosen_instr = snapshot_warning if is_restricted else standard_instructions
        
        return f"""
        [MISSION PROGRESS]
        {state.task_intent}
        
        [CRITICAL GROUND TRUTH (The Backpack)]
        You currently hold the following persistent Artifacts: {artifacts_summary}
        Your Active L1 RAM contains: {l1_files}
        
        {l1_warning}
        {feedback_alert}
        
        ### OPERATIONAL INSTRUCTIONS ###
        {chosen_instr}

        [ENVIRONMENT STRUCTURE]
        {map_block}

        {history_block}
        
        [CURRENT L1 CONTEXT CONTENT]
        {active_content}

        [DECISION RULES]
        1. MISSION FIRST: Look at your 'Completed Artifacts'. What is MISSING? Only stage files for MISSING data.
        2. IF you have an artifact (e.g. 'PROTOCOL'), DO NOT stage its source file again.
        3. IF you need a new file and L1 already contains a user file, you MUST use 'unstage_context' first.
        4. IF you have all artifacts, use 'calculate' or 'verify_step' then 'save_artifact(TOTAL...)'.
        5. TRUST your artifacts. They are your persistent memory.
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
