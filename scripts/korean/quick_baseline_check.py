#!/usr/bin/env python3
import subprocess
import sys
import os

# Add paths
sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/regions/e_groups/e4_korea')

os.chdir('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/regions/e_groups/e4_korea')

# Run test on current state
print("Testing current state...")
result = subprocess.run([sys.executable, 'test_accuracy.py', 'data/korean.yaml'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    print(result.stdout)
    
    # Extract the summary line
    for line in result.stdout.split('\n'):
        if '=== SUMMARY ===' in line:
            summary_start = True
        elif 'Mathematician dataset:' in line:
            print("\nCurrent accuracy:")
            print(line)
else:
    print("Error running test:")
    print(result.stderr)