from amnesic.core.session import AmnesicSession

class MediatorSession(AmnesicSession):
    """
    A specialized session for Conflict Resolution (The 'Blind Mediator').
    Utilizes the Dual-Slot Comparator to safely analyze two diverging files
    side-by-side without permanently polluting the context.
    
    Protocol:
    1. Identify conflicting files (File A, File B).
    2. Invoke 'compare_files(A, B)' to load both into 'Comparator Slots'.
    3. Generate a 'Conflict Resolution Artifact' (The Merge Plan).
    4. Auto-Eviction triggers immediately (Atomic Purge).
    5. Apply the resolution.
    """

    def __init__(self, mission: str, **kwargs):
        mediator_constraints = (
            "CONFLICT RESOLUTION PROTOCOL ACTIVE. "
            "1. You are the MEDIATOR. "
            "2. You have access to the 'compare_files' tool which temporarily expands your context. "
            "3. DO NOT try to read both files sequentially with 'stage_context' (You will drift). "
            "4. Use 'compare_files(file_a, file_b)' to generate a 'MERGED_' artifact. "
            "5. Then use 'write_file(resolved.py: ARTIFACT:MERGED_...)' to save the resolution."
        )
        full_mission = f"{mission}\n\n{mediator_constraints}"
        super().__init__(mission=full_mission, **kwargs)
