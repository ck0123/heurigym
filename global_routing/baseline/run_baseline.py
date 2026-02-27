#!/usr/bin/env python3
"""
# https://github.com/cuhk-eda/InstantGR
Run InstantGR on all global routing test cases and collect baseline costs.
Updates baseline.json with the actual costs.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
INSTANTGR_RUN = SCRIPT_DIR / "InstantGR" / "run"
INSTANTGR_BIN = INSTANTGR_RUN / "InstantGR"
PROGRAM_DIR = SCRIPT_DIR.parent / "program"
EVALUATOR_BIN = PROGRAM_DIR / "evaluator"
DATASET_ROOT = REPO_ROOT / "_datasets" / "global_routing"
BASELINE_JSON = SCRIPT_DIR / "baseline.json"

DATASET_SPLITS = ["demo", "eval"]


def run_instantgr(cap_file: Path, net_file: Path, out_file: Path) -> bool:
    """Run InstantGR on a single test case. Returns True on success."""
    result = subprocess.run(
        [str(INSTANTGR_BIN), "-cap", str(cap_file), "-net", str(net_file), "-out", str(out_file)],
        cwd=str(INSTANTGR_RUN),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        print(f"  InstantGR failed (rc={result.returncode})")
        if result.stderr:
            print(f"  stderr: {result.stderr[:500]}")
        return False
    return True


def evaluate(cap_file: Path, net_file: Path, out_file: Path) -> float:
    """Run heurigym evaluator and return the total cost."""
    result = subprocess.run(
        [str(EVALUATOR_BIN), str(cap_file), str(net_file), str(out_file)],
        cwd=str(PROGRAM_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Evaluator failed (rc={result.returncode}): {result.stderr}")
    lines = result.stdout.strip().split("\n")
    last = lines[-1]
    if not last.startswith("total cost"):
        raise ValueError(f"Unexpected evaluator output: {last}")
    return float(last.split()[-1])


def main():
    results = {}

    for split in DATASET_SPLITS:
        split_dir = DATASET_ROOT / split
        if not split_dir.exists():
            print(f"Split directory not found: {split_dir}")
            continue

        cap_files = sorted(split_dir.glob("*.cap"))
        print(f"\n=== {split}: {len(cap_files)} test cases ===")

        for cap_file in cap_files:
            name = cap_file.stem
            net_file = cap_file.with_suffix(".net")
            if not net_file.exists():
                print(f"  [{name}] SKIP: missing .net file")
                continue

            print(f"  [{name}] Running InstantGR...", end="", flush=True)
            with tempfile.NamedTemporaryFile(suffix=".out", delete=False) as tmp:
                out_file = Path(tmp.name)
            try:
                success = run_instantgr(cap_file, net_file, out_file)
                if not success:
                    results[name] = None
                    continue

                cost = evaluate(cap_file, net_file, out_file)
                results[name] = cost
                print(f" cost = {cost:.2f}")
            except Exception as e:
                print(f" ERROR: {e}")
                results[name] = None
            finally:
                if out_file.exists():
                    out_file.unlink()

    # Write results
    print(f"\nWriting {len(results)} results to {BASELINE_JSON}")
    with open(BASELINE_JSON, "w") as f:
        json.dump(results, f, indent=4)

    # Summary
    failed = [k for k, v in results.items() if v is None]
    if failed:
        print(f"\nFailed cases ({len(failed)}): {failed}")
    else:
        print(f"\nAll {len(results)} cases completed successfully.")


if __name__ == "__main__":
    main()
