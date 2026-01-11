from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field, field_validator
from ..drivers.ollama import OllamaDriver

# The Worker's Output Schema
class GenerationArtifact(BaseModel):
    file_path: str = Field(default="extracted_value", description="The file being created or modified")
    content: str = Field(..., description="The complete text or code content")
    verification_notes: str = Field(default="Extraction complete", description="Self-check: Does this meet the constraints?")

    @field_validator('content', mode='before')
    def coerce_to_string(cls, v):
        return str(v) if v is not None else ""

    @field_validator('content')
    def physical_payload_check(cls, v):
        # Limit to 1MB to prevent system memory saturation
        if len(v) > 1_000_000:
            raise ValueError("Physical Payload Limit Exceeded: Generated content exceeds 1MB.")
        return v

class CodeEdit(BaseModel):
    original_snippet: str = Field(..., description="The exact text segment to replace (must match unique location).")
    new_snippet: str = Field(..., description="The new text to insert.")
    verification_notes: str = Field(default="Edit generated", description="Why this edit fixes the issue.")

    @field_validator('new_snippet')
    def physical_payload_check(cls, v):
        if len(v) > 1_000_000:
            raise ValueError("Physical Payload Limit Exceeded: Edit snippet exceeds 1MB.")
        return v

class Worker:
    def __init__(self, driver: OllamaDriver):
        self.driver = driver

    def execute_task(self, task_description: str, active_context: str, constraints: list[str]) -> GenerationArtifact:
        """
        Spins up a 'Production' frame.
        This frame has NO memory of the Plan, only the immediate Task.
        """
        
        system_prompt = f"""
        You are a STRUCTURAL ANALYST and Value Extractor.
        
        Variable names in the context may be intentionally misleading (lying). 
        IGNORE the names; focus on the data structure and extract the primary value found.
        
        YOUR CONSTRAINTS:
        {chr(10).join(f"- {c}" for c in constraints)}
        
        INSTRUCTIONS:
        1. Read the Context.
        2. Find the requested data or value based on its role, not just its name.
        3. Even if the task asks for a 'raw' value, you MUST return it as a valid JSON object matching the schema.
        4. Place the extracted value in the 'content' field of the JSON.
        5. Do not converse.
        """

        user_prompt = f"""
        [CONTEXT BEGIN]
        {active_context}
        [CONTEXT END]

        TASK: {task_description}
        
        Generate the content now.
        """

        return self.driver.generate_structured(
            user_prompt=user_prompt,
            schema=GenerationArtifact,
            system_prompt=system_prompt,
            retries=3
        )

    def perform_edit(self, target_file: str, instructions: str, active_context: str, constraints: list[str]) -> CodeEdit:
        """
        Performs a surgical edit on a file.
        """
        system_prompt = f"""
        You are the CODE EDITOR. You perform surgical text replacements.
        
        YOUR CONSTRAINTS:
        {chr(10).join(f"- {c}" for c in constraints)}
        
        INSTRUCTIONS:
        1. Locate the code block that needs changing based on the instructions.
        2. Provide the 'original_snippet' EXACTLY as it appears in the file.
        3. Provide the 'new_snippet' with the requested changes.
        4. Ensure indentation matches.
        5. OUTPUT RAW JSON ONLY. Do NOT use markdown code fences (```json).
        """

        user_prompt = f"""
        [CONTEXT BEGIN]
        {active_context}
        [CONTEXT END]

        TARGET FILE: {target_file}
        INSTRUCTIONS: {instructions}
        
        Generate the edit now.
        """

        return self.driver.generate_structured(
            user_prompt=user_prompt,
            schema=CodeEdit,
            system_prompt=system_prompt,
            retries=3
        )
