#!/usr/bin/env python3
# Convenience wrapper to run monitor_memory_profile.py against a module:function with sensible defaults.
import json
import subprocess
import sys

mod = sys.argv[1] if len(sys.argv) > 1 else "tools.generate_scale_dataset:main"
args = [
    "python",
    "tools/monitor_memory_profile.py",
    "--module",
    mod,
    "--args",
    "[]",
    "--kwargs",
    "{}",
    "--top",
    "25",
]
print(subprocess.check_output(args, text=True))
