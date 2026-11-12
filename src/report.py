"""Collect every run's test predictions, run the paired patient bootstrap, write tables.

    python src/report.py --runs "runs/*" --out results/

Outputs
-------
results/results_long.csv   model x metric with point estimate and 95% CI
results/diffs.csv          paired differences vs the reference model
results/results.md         the table in markdown, ready to paste into the report

Runs without a `test_preds.csv` are skipped, so this is safe to run mid-project.
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

from bootstrap import patient_bootstrap, to_frame
from metrics import summary


def load_runs(patterns, split_suffix="test_preds.csv"):
    runs = {}
    for pat in patterns:
        for p in sorted(glob.glob(pat)):
            if os.path.isdir(p):
                name = os.path.basename(os.path.normpath(p))
                f = os.path.join(p, split_suffix)
                if os.path.exists(f):
                    runs[name] = f
    return runs


def _md(df):
    """to_markdown needs `tabulate`, which is not always installed; degrade gracefully."""
    try:
        return df.to_markdown()
    except Exception:
        return df.to_string()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=["runs/*"])
    ap.add_argument("--out", default="results")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--spec", type=float, default=0.80)
    ap.add_argument("--reference", default=None, help="model name for pairwise contrasts")
    args = ap.parse_args()

    runs = load_runs(args.runs)
    if not runs:
        raise SystemExit("no runs with test_preds.csv found")
    print("found:", ", ".join(runs))

    base = None
    for name, path in runs.items():
        f = pd.read_csv(path)
        f = f.rename(columns={"prob": name})[["image_name", "patient_id", "target", name]]
        base = f if base is None else base.merge(
            f.drop(columns=["patient_id", "target"]), on="image_name", how="inner")

    # sanity: every model must cover the identical set of images
    assert base["image_name"].is_unique, "duplicate image_name after merge"
    print(f"{len(base)} images, {int(base.target.sum())} melanomas, "
          f"{base.patient_id.nunique()} patients")

    res = patient_bootstrap(base, list(runs), n_boot=args.n_boot, seed=args.seed,
                            spec=args.spec)
    os.makedirs(args.out, exist_ok=True)
    tbl = to_frame(res)
    tbl.to_csv(os.path.join(args.out, "results_long.csv"), index=False)

    ref = args.reference or list(runs)[0]
    rows = []
    for pair, mets in res["diff"].items():
        if ref not in pair:
            continue
        for m, d in mets.items():
            rows.append({"contrast": pair, "metric": m, "delta": d["delta"],
                         "ci_lo": d["lo"], "ci_hi": d["hi"], "p": d["p_two_sided"],
                         "ci_str": f'{d["delta"]:+.3f} [{d["lo"]:+.3f}, {d["hi"]:+.3f}]'})
    dff = pd.DataFrame(rows)
    dff.to_csv(os.path.join(args.out, "diffs.csv"), index=False)

    pivot = tbl.pivot(index="model", columns="metric", values="ci_str")
    with open(os.path.join(args.out, "results.md"), "w") as fh:
        fh.write(_md(pivot) + "\n\n")
        fh.write(_md(dff[["contrast", "metric", "ci_str", "p"]]) + "\n")
    print(pivot.to_string())

    # per-model headline metrics with the calibration slope, for the appendix
    detail = {}
    for name in runs:
        detail[name] = summary(base["target"].to_numpy(), base[name].to_numpy(),
                               spec=args.spec, with_slope=True)
    with open(os.path.join(args.out, "summary.json"), "w") as fh:
        json.dump(detail, fh, indent=2)
    print(f"\nwrote -> {args.out}/results_long.csv, diffs.csv, results.md, summary.json")


if __name__ == "__main__":
    main()
