#!/usr/bin/env python3
import argparse, subprocess, json

ap = argparse.ArgumentParser()
ap.add_argument("--profile", choices=["test", "prod"], required=True)
ap.add_argument("--in", dest="inp", required=True)
a = ap.parse_args()
cfg = f"config/gates.{a.profile}.yaml"
print(json.dumps({"profile": a.profile, "config": cfg, "input": a.inp}, indent=2))
subprocess.check_call(["python", "-m", "src.quality.quality_gates", "--in", a.inp, "--gates", cfg])
