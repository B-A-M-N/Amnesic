import re

goal = "MISSION: Reconstruct a 10-word sentence by following the trail from step_0.txt to step_9.txt. Extract each PART_N and save it as an artifact. Once you have all 10 parts, combine them into a single 'TOTAL' result and HALT."

count_match = re.search(r'(\d+)[\s-](?:word|part|file|artifact|step)', goal.lower())
if count_match:
    required_count = int(count_match.group(1))
    print(f"Matched: {count_match.group(0)}")
    print(f"Required Count: {required_count}")
else:
    print("No match found.")

# Let's test with just 9 artifacts
current_artifacts = [f"PART_{i}" for i in range(9)]
print(f"Artifacts count: {len(current_artifacts)}")
if len(current_artifacts) < required_count:
    print("REJECTED (Correct)")
else:
    print("PASSED (Incorrect behavior for this test)")
