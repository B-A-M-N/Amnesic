from amnesic.core.session import AmnesicSession

class RosettaSession(AmnesicSession):
    """
    A specialized session for Legacy Migration (The 'Rosetta Stone' pattern).
    Enforces a 'Schema-Driven Translation':
    1. Load Legacy File (L1)
    2. Load Target Schema (Artifact/Sidecar)
    3. Generate New Code (Artifact)
    4. Evict Legacy (L1 Purge)
    """

    def __init__(self, mission: str, **kwargs):
        rosetta_constraints = (
            "MIGRATION PROTOCOL ACTIVE. "
            "1. You are the ROSETTA TRANSLATOR. "
            "2. Input is LEGACY CODE (Spaghetti/Global state). "
            "3. Goal is MODERN PYTHON (Clean/Typed). "
            "4. You MUST strictly adhere to the provided SCHEMA ARTIFACTS. "
            "5. Do NOT preserve legacy naming conventions if they violate the Schema. "
            "6. Once translated, save the new code as an Artifact."
        )
        full_mission = f"{mission}\n\n{rosetta_constraints}"
        super().__init__(mission=full_mission, **kwargs)
        
        from .code_agent import Artifact
        self.state['framework_state'].artifacts.append(
            Artifact(
                identifier="EmployeeSchema",
                type="config",
                summary="@dataclass class Employee: name: str, hourly_rate: float, hours_worked: float",
                status="verified_invariant"
            )
        )
