from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class RefactorSession(AmnesicSession):
    """
    A specialized session for code quality and modernization.
    Enforces 'Behavioral Invariance':
    1. Read Source (L1)
    2. Identify Structural Improvements (Thought)
    3. Apply PEP8/Typing (Edit)
    4. Ensure Logic is unchanged.
    """

    def __init__(self, mission: str, **kwargs):
        refactor_protocol = (
            "REFACTORING PROTOCOL ACTIVE. "
            "1. You are the REFACTORING ENGINEER. "
            "2. Goal: Improve readability, PEP8 compliance, and type-safety. "
            "3. Constraint: DO NOT change the functional logic or external API. "
            "4. Requirement: Every function MUST have type hints for arguments and return values. "
            "5. Requirement: Replace complex nested logic with guard clauses where possible. "
        )
        full_mission = f"{mission}\n\n{refactor_protocol}"
        super().__init__(mission=full_mission, **kwargs)
        
        # Inject standard style guide
        self.state['framework_state'].artifacts.append(
            Artifact(
                identifier="STYLE_GUIDE",
                type="config",
                summary="Standard: PEP8. Max Line Length: 88. Use snake_case. Use Google-style docstrings.",
                status="verified_invariant"
            )
        )

