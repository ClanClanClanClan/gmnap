import subprocess, json, os, pathlib, sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
KOREAN_DIR = REPO_ROOT / "src" / "gmnap" / "regions" / "e_groups" / "e4_korea"
RESULTS = {}


def run(cmd, cwd=None, quiet=True):
    kw = dict(cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc = subprocess.run(cmd, **kw)
    if proc.returncode and not quiet:
        print(f"Command failed: {cmd}")
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
    return proc


# Get recent commits
all_shas = (
    run("git rev-list --max-count=10 HEAD", cwd=REPO_ROOT, quiet=False).stdout.strip().splitlines()
)

print(f"Scanning {len(all_shas)} recent commits...")

for i, sha in enumerate(all_shas):
    print(f"\nChecking commit {i+1}/{len(all_shas)}: {sha[:8]}")

    # Stash any local changes
    run("git stash", cwd=REPO_ROOT, quiet=True)

    # Checkout the commit
    if run(f"git checkout {sha} --quiet", cwd=REPO_ROOT).returncode:
        print(f"  Failed to checkout {sha}")
        continue

    # Check if test script exists
    test_script = KOREAN_DIR / "test_accuracy.py"
    if not test_script.exists():
        print(f"  No test script in this commit")
        continue

    # Check if FST models exist, if not try to build them
    models_dir = KOREAN_DIR / "models"
    if not models_dir.exists() or not any(models_dir.glob("*.fst")):
        print(f"  No models found, attempting to build...")
        build_scripts = [
            KOREAN_DIR / "scripts" / "build_fsts_multi.py",
            KOREAN_DIR / "build_fsts.py",
            KOREAN_DIR / "src" / "build_fsts.py",
        ]

        built = False
        for build_script in build_scripts:
            if build_script.exists():
                if run(f"cd {KOREAN_DIR} && python3 {build_script}", quiet=True).returncode == 0:
                    print(f"  Built models successfully")
                    built = True
                    break

        if not built:
            print(f"  Could not build models")
            continue

    # Run tests
    korean_data = KOREAN_DIR / "data" / "korean.yaml"
    diverse_data = KOREAN_DIR / "data" / "korean_diverse_test.yaml"

    if not korean_data.exists():
        print(f"  No korean.yaml data file")
        continue

    # Run mathematician test
    r1 = run(f"cd {KOREAN_DIR} && python3 test_accuracy.py data/korean.yaml", quiet=True)
    if r1.returncode:
        print(f"  Mathematician test failed")
        continue

    # Run diverse test
    r2 = run(
        f"cd {KOREAN_DIR} && python3 test_accuracy.py data/korean_diverse_test.yaml", quiet=True
    )
    if r2.returncode:
        print(f"  Diverse test failed")
        # Still record math results

    # Parse results
    try:
        m_ok = m_tot = 0
        d_ok = d_tot = 0

        # Extract mathematician dataset accuracy
        for line in r1.stdout.split("\n"):
            if "Eng2Kor:" in line and "/" in line:
                parts = line.split()
                for part in parts:
                    if "/" in part:
                        m_ok, m_tot = map(int, part.split("/"))
                        break

        # Extract diverse dataset accuracy if available
        if r2.returncode == 0:
            for line in r2.stdout.split("\n"):
                if "Eng2Kor:" in line and "/" in line:
                    parts = line.split()
                    for part in parts:
                        if "/" in part:
                            d_ok, d_tot = map(int, part.split("/"))
                            break

        RESULTS[sha] = (m_ok, d_ok)

        # Get commit message
        msg = run(f"git log -1 --pretty=format:'%s' {sha}", cwd=REPO_ROOT).stdout.strip()
        print(
            f"  Math: {m_ok}/{m_tot} ({100*m_ok/m_tot:.1f}%), Diverse: {d_ok}/{d_tot if d_tot else 0} ({100*d_ok/d_tot if d_tot else 0:.1f}%)"
        )
        print(f"  Message: {msg}")

    except Exception as e:
        print(f"  Failed to parse results: {e}")
        continue

# Restore original state
print("\nRestoring original state...")
run("git checkout v6_empirical_baseline", cwd=REPO_ROOT, quiet=True)
run("git stash pop", cwd=REPO_ROOT, quiet=True)

if RESULTS:
    print("\n=== RESULTS SUMMARY ===")
    sorted_results = sorted(RESULTS.items(), key=lambda kv: (kv[1][0] + kv[1][1]), reverse=True)

    for sha, (m, d) in sorted_results[:5]:
        msg = run(f"git log -1 --pretty=format:'%s' {sha}", cwd=REPO_ROOT).stdout.strip()
        print(f"{sha[:8]}: Math={m}, Diverse={d}, Total={m+d} - {msg}")

    best = sorted_results[0]
    print(f"\nBest commit: {best[0][:8]} with Math={best[1][0]}, Diverse={best[1][1]}")

    # Save results
    result_data = {
        "best_sha": best[0],
        "math": best[1][0],
        "div": best[1][1],
        "all_results": {sha: {"math": m, "diverse": d} for sha, (m, d) in RESULTS.items()},
    }

    output_file = REPO_ROOT / "baseline_scan.json"
    output_file.write_text(json.dumps(result_data, indent=2))
    print(f"\nResults saved to {output_file}")
else:
    print("\nNo valid results found")
