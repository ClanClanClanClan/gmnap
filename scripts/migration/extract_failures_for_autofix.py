#!/usr/bin/env python3
"""Extract failures from test_diverse_dataset.py output for auto-fix analysis"""

import subprocess
import re
import json

# Run test_diverse_dataset.py and capture output
result = subprocess.run(["python3", "test_diverse_dataset.py"], capture_output=True, text=True)

output = result.stdout

# Extract failure information using regex
failures = []

# Pattern to extract failures from the output
# Looking for lines like: "1. Name_Here"
#                        "Type: eng→kor"
#                        "Expected: 한글"
#                        "Actual: 다른한글 or None"

lines = output.split("\n")
i = 0
while i < len(lines):
    # Look for numbered failure entries
    match = re.match(r"\s*\d+\.\s+(.+)", lines[i])
    if match:
        name = match.group(1).strip()

        # Extract details from following lines
        failure_info = {"name": name}

        # Look for Type, Expected, Actual in next few lines
        for j in range(i + 1, min(i + 10, len(lines))):
            if "Type:" in lines[j]:
                failure_info["type"] = lines[j].split("Type:")[1].strip()
            elif "Expected:" in lines[j]:
                failure_info["expected"] = lines[j].split("Expected:")[1].strip()
            elif "Actual:" in lines[j]:
                actual = lines[j].split("Actual:")[1].strip()
                failure_info["actual"] = None if actual == "None" else actual
            elif "Reason:" in lines[j]:
                failure_info["reason"] = lines[j].split("Reason:")[1].strip()
                break

        if "type" in failure_info and failure_info["type"] == "eng→kor":
            failures.append(failure_info)

    i += 1

# Also extract accuracy information
accuracy_match = re.search(r"Diverse Dataset:\s*([\d.]+)%\s*accuracy", output)
if accuracy_match:
    diverse_accuracy = float(accuracy_match.group(1))
else:
    diverse_accuracy = None

# Extract total failures count
total_match = re.search(r"English→Korean failures:\s*(\d+)", output)
if total_match:
    total_failures = int(total_match.group(1))
else:
    total_failures = len(failures)

print(f"Extracted {len(failures)} failures from diverse dataset")
print(f"Diverse dataset accuracy: {diverse_accuracy}%")

# Save failures for auto-fix analysis
with open("diverse_failures.json", "w", encoding="utf-8") as f:
    json.dump(
        {"accuracy": diverse_accuracy, "total_failures": total_failures, "failures": failures},
        f,
        indent=2,
        ensure_ascii=False,
    )

print("\nFirst 5 failures:")
for i, failure in enumerate(failures[:5]):
    print(f"{i+1}. {failure['name']}: {failure['expected']} → {failure.get('actual', 'None')}")
