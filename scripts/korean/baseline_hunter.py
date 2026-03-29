import subprocess, json, os, pathlib, csv, yaml, sys, shutil
from tempfile import TemporaryDirectory
from tqdm import tqdm

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MATH_SCRIPT = (
    REPO_ROOT
    / "src"
    / "gmnap"
    / "regions"
    / "e_groups"
    / "e4_korea"
    / "test_accuracy.py"
)
DIVERSE_SCRIPT = (
    REPO_ROOT
    / "src"
    / "gmnap"
    / "regions"
    / "e_groups"
    / "e4_korea"
    / "test_accuracy.py"
)
BUILD_SCRIPT = (
    REPO_ROOT
    / "src"
    / "gmnap"
    / "regions"
    / "e_groups"
    / "e4_korea"
    / "scripts"
    / "build_fsts_multi.py"
)
RESULTS = {}


def run(cmd, cwd=None, quiet=True):
    kw = dict(
        cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    proc = subprocess.run(cmd, **kw)
    if proc.returncode and not quiet:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
    return proc


all_shas = (
    run("git rev-list --max-count=200 --reverse HEAD", cwd=REPO_ROOT, quiet=False)
    .stdout.strip()
    .splitlines()
)

with TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    for sha in tqdm(all_shas, desc="Scanning commits"):
        run(f"git checkout {sha} --quiet", cwd=REPO_ROOT)
        # Clean build artefacts
        models_path = (
            REPO_ROOT / "src" / "gmnap" / "regions" / "e_groups" / "e4_korea" / "models"
        )
        if models_path.exists():
            shutil.rmtree(models_path)

        # Check if build script exists in this commit
        if not BUILD_SCRIPT.exists():
            continue

        if run(f"python3 {BUILD_SCRIPT}", cwd=REPO_ROOT, quiet=True).returncode:
            continue  # build failed

        # Run tests with Korean data files
        korean_data = (
            REPO_ROOT
            / "src"
            / "gmnap"
            / "regions"
            / "e_groups"
            / "e4_korea"
            / "data"
            / "korean.yaml"
        )
        diverse_data = (
            REPO_ROOT
            / "src"
            / "gmnap"
            / "regions"
            / "e_groups"
            / "e4_korea"
            / "data"
            / "korean_diverse_test.yaml"
        )

        r1 = run(f"python3 {MATH_SCRIPT} {korean_data}", cwd=REPO_ROOT, quiet=True)
        r2 = run(f"python3 {DIVERSE_SCRIPT} {diverse_data}", cwd=REPO_ROOT, quiet=True)

        if r1.returncode or r2.returncode:
            continue

        # Parse output - looking for "Eng2Kor: X/Y" pattern
        try:
            # Extract mathematician dataset accuracy
            for line in r1.stdout.split("\n"):
                if "Eng2Kor:" in line and "/" in line:
                    parts = line.split()
                    for part in parts:
                        if "/" in part:
                            m_ok, m_tot = map(int, part.split("/"))
                            break

            # Extract diverse dataset accuracy
            for line in r2.stdout.split("\n"):
                if "Eng2Kor:" in line and "/" in line:
                    parts = line.split()
                    for part in parts:
                        if "/" in part:
                            d_ok, d_tot = map(int, part.split("/"))
                            break

        except Exception as e:
            print(f"Failed to parse output for {sha}: {e}")
            continue

        RESULTS[sha] = (m_ok, d_ok)
        print(f"SHA {sha[:8]}: Math {m_ok}/{m_tot}, Diverse {d_ok}/{d_tot}")

    # restore HEAD
    run("git checkout -", cwd=REPO_ROOT, quiet=True)

if RESULTS:
    best = max(RESULTS.items(), key=lambda kv: (kv[1][0] + kv[1][1]))
    print(json.dumps({"best_sha": best[0], "math": best[1][0], "div": best[1][1]}))
    pathlib.Path(REPO_ROOT / "baseline_scan.json").write_text(
        json.dumps(RESULTS, indent=2)
    )
else:
    print("No valid results found")
