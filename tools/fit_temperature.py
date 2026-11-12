"""Fit a temperature on the validation split and apply it to the test split.

    python tools/fit_temperature.py --run-dir runs/b3_wbce

Reads `val_preds.csv` + `test_preds.csv` from the run directory (produced by
`src/evaluate.py --split val|test`), writes `test_preds_temp.csv`, and prints the
before/after table that goes into the report as the "does post-hoc calibration fix it"
row. Uses numpy only, so it runs without a GPU and without torch.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from metrics import apply_temperature, summary, temperature_nll   # noqa: E402

COLS = ["auroc", "auprc", "brier", "nll", "ece_uniform15", "ece_adaptive15",
        "ece_pos", "sens_at_spec80", "cal_slope"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="e.g. runs/b3_wbce")
    ap.add_argument("--val", default="val_preds.csv")
    ap.add_argument("--test", default="test_preds.csv")
    args = ap.parse_args()

    d = args.run_dir
    va = pd.read_csv(os.path.join(d, args.val))
    te = pd.read_csv(os.path.join(d, args.test))

    p = np.clip(va["prob"].to_numpy(), 1e-6, 1 - 1e-6)
    T = temperature_nll(va["target"].to_numpy(), np.log(p / (1 - p)))

    before = summary(te["target"].to_numpy(), te["prob"].to_numpy(), with_slope=True)
    out = te.copy()
    out["prob"] = apply_temperature(te["prob"].to_numpy(), T)
    after = summary(out["target"].to_numpy(), out["prob"].to_numpy(), with_slope=True)

    out.to_csv(os.path.join(d, "test_preds_temp.csv"), index=False)

    print(f"run            : {d}")
    print(f"optimal T (val): {T:.3f}   ({'over' if T > 1 else 'under'}-confident before scaling)")
    print(f"1/T            : {1 / T:.3f}   should be close to cal_slope before scaling "
          f"({before['cal_slope']:.3f})")
    print()
    print(f"{'metric':16s} {'before':>9s} {'after':>9s} {'delta':>9s}")
    for c in COLS:
        b, a = before.get(c), after.get(c)
        if b is None or a is None or not np.isfinite(b) or not np.isfinite(a):
            continue
        print(f"{c:16s} {b:9.4f} {a:9.4f} {a - b:+9.4f}")

    with open(os.path.join(d, "temperature.json"), "w") as fh:
        json.dump({"T": T, "before": before, "after": after}, fh, indent=2)
    print(f"\nwrote {os.path.join(d, 'test_preds_temp.csv')} and temperature.json")


if __name__ == "__main__":
    main()
