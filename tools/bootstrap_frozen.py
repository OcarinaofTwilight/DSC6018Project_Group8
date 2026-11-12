"""Patient-level bootstrap with the operating threshold frozen at its validation value.

`src/report.py` re-estimates the threshold inside every resample (useful, but it reports a
slightly optimistic sensitivity because the threshold adapts to the resample). For the
report we want the honest protocol: threshold fixed once on validation, then bootstrap
the patients only.

    <venv>\\Scripts\\python.exe tools/bootstrap_frozen.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from metrics import (auprc, auroc, brier, ece, net_benefit, partial_auroc,   # noqa: E402
                     sens_at_spec, threshold_at_specificity)

RUNS = ["b3_bce", "b3_wbce", "b3_focal", "r50_bce", "b3_bce_meta"]
N_BOOT = 2000
SEED = 42


def metrics_at_frozen(y, p, thr, spec=0.80):
    sens, achieved, _ = sens_at_spec(y, p, spec, threshold=thr)
    return {
        "auroc": auroc(y, p),
        "auprc": auprc(y, p),
        "pauc_fpr20": partial_auroc(y, p, 0.20),
        "brier": brier(y, p),
        "ece_adaptive15": ece(y, p, bins=15, mode="quantile"),
        "sens_at_spec80": sens,
        "spec_achieved": achieved,
    }


def main():
    base = None
    thresholds = {}
    for r in RUNS:
        va = pd.read_csv(os.path.join(ROOT, "runs", r, "val_preds.csv"))
        thresholds[r] = float(threshold_at_specificity(va.target.values, va.prob.values, 0.80))
        te = pd.read_csv(os.path.join(ROOT, "runs", r, "test_preds.csv"))
        te = te.rename(columns={"prob": r})[["image_name", "patient_id", "target", r]]
        base = te if base is None else base.merge(te.drop(columns=["patient_id", "target"]),
                                                  on="image_name")

    y = base.target.values.astype(int)
    pat = base.patient_id.values
    codes, uniq = pd.factorize(pat)
    order = np.argsort(codes, kind="mergesort")
    bounds = np.r_[0, np.flatnonzero(np.diff(codes[order])) + 1, order.size]
    groups = [order[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]
    n_pat = len(groups)

    point = {r: metrics_at_frozen(y, base[r].values, thresholds[r]) for r in RUNS}

    rng = np.random.default_rng(SEED)
    draws = {r: {m: [] for m in point[r]} for r in RUNS}
    for _ in range(N_BOOT):
        pick = rng.integers(0, n_pat, n_pat)
        idx = np.concatenate([groups[i] for i in pick])
        yb = y[idx]
        if yb.sum() == 0:
            continue
        for r in RUNS:
            mb = metrics_at_frozen(yb, base[r].values[idx], thresholds[r])
            for k, v in mb.items():
                draws[r][k].append(v)

    out = {"thresholds": thresholds, "n_boot": N_BOOT, "point": point, "ci": {}}
    for r in RUNS:
        out["ci"][r] = {m: [float(np.nanpercentile(draws[r][m], 2.5)),
                            float(np.nanpercentile(draws[r][m], 97.5))] for m in point[r]}

    # paired differences vs BCE
    out["diff_vs_bce"] = {}
    for r in RUNS[1:]:
        out["diff_vs_bce"][r] = {}
        for m in point[r]:
            d = np.array(draws[r][m]) - np.array(draws[RUNS[0]][m])
            lo, hi = np.nanpercentile(d, 2.5), np.nanpercentile(d, 97.5)
            p = 2 * min(np.nanmean(d <= 0), np.nanmean(d >= 0))
            out["diff_vs_bce"][r][m] = {
                "delta": point[r][m] - point[RUNS[0]][m],
                "lo": float(lo), "hi": float(hi), "p": float(p),
            }

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    path = os.path.join(ROOT, "results", "bootstrap_frozen.json")
    json.dump(out, open(path, "w"), indent=2)
    print("wrote", path)
    for r in RUNS:
        s, c = point[r], out["ci"][r]
        print(f"{r:13s} sens {s['sens_at_spec80']:.3f} [{c['sens_at_spec80'][0]:.3f},"
              f"{c['sens_at_spec80'][1]:.3f}]  auroc {s['auroc']:.3f} "
              f"[{c['auroc'][0]:.3f},{c['auroc'][1]:.3f}]  auprc {s['auprc']:.3f} "
              f"[{c['auprc'][0]:.3f},{c['auprc'][1]:.3f}]  ece {s['ece_adaptive15']:.4f} "
              f"[{c['ece_adaptive15'][0]:.4f},{c['ece_adaptive15'][1]:.4f}]")
    print()
    for r, mets in out["diff_vs_bce"].items():
        row = ", ".join(f"{m}: {v['delta']:+.3f} [{v['lo']:+.3f},{v['hi']:+.3f}] p={v['p']:.3f}"
                        for m, v in mets.items()
                        if m in ("sens_at_spec80", "auroc", "auprc", "brier", "ece_adaptive15"))
        print(f"{r} vs b3_bce -> {row}")


if __name__ == "__main__":
    main()
