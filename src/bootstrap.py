"""Patient-level bootstrap for the calibration benchmark.

Two design decisions that are easy to get wrong and that reviewers will ask about:

1. Resample *patients*, not images. Images from one patient are not independent; an
   image-level bootstrap underestimates the CI width by roughly sqrt(images/patient).
2. Resample *paired*: every model is evaluated on exactly the same resampled patient
   set, so the CI of a difference is a bootstrap of the paired difference rather than
   the difference of two independent CIs. The latter is far too conservative and will
   hide a real effect.

The threshold for Sens@Spec80 is re-estimated inside each resample (fully
non-parametric), so the CI includes threshold-selection noise.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from metrics import auprc, auroc, brier, ece, partial_auroc, sens_at_spec


DEFAULT_METRICS = ("auroc", "auprc", "pauc_fpr20", "brier", "ece_adaptive15", "sens_at_spec80")


def _metric_value(name, y, p, spec):
    """Dispatch straight to the metric function (no summary() call: 2000x faster)."""
    if name == "auroc":
        return auroc(y, p)
    if name == "auprc":
        return auprc(y, p)
    if name == "pauc_fpr20":
        return partial_auroc(y, p, 0.20)
    if name == "brier":
        return brier(y, p)
    if name == "ece_adaptive15":
        return ece(y, p, bins=15, mode="quantile")
    if name == "ece_uniform15":
        return ece(y, p, bins=15, mode="uniform")
    if name == "ece_pos":
        return ece(y, p, bins=15, mode="quantile", subset="pos")
    if name.startswith("sens_at_spec"):
        return sens_at_spec(y, p, spec=int(name.replace("sens_at_spec", "")) / 100.0)[0]
    raise ValueError(f"unknown metric {name!r}")


def patient_bootstrap(
    df: pd.DataFrame,
    prob_cols,
    patient_col: str = "patient_id",
    label_col: str = "target",
    n_boot: int = 2000,
    seed: int = 42,
    spec: float = 0.80,
    metrics=DEFAULT_METRICS,
    alpha: float = 0.05,
) -> dict:
    """Return point estimates, percentile CIs and paired differences.

    df must have one row per image with `patient_col`, `label_col` and one column per
    model containing the predicted melanoma probability.
    """
    df = df.reset_index(drop=True)
    y_all = df[label_col].to_numpy().astype(int)

    # patient -> row indices (computed once, reused 2000 times)
    patient_codes, uniques = pd.factorize(df[patient_col], sort=True)
    order = np.argsort(patient_codes, kind="mergesort")
    bounds = np.r_[0, np.flatnonzero(np.diff(patient_codes[order])) + 1, order.size]
    groups = [order[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]
    n_patients = len(groups)

    probs = {c: df[c].to_numpy(dtype=float) for c in prob_cols}

    point = {
        c: {m: _metric_value(m, y_all, probs[c], spec) for m in metrics} for c in prob_cols
    }

    rng = np.random.default_rng(seed)
    draws = {c: {m: np.full(n_boot, np.nan) for m in metrics} for c in prob_cols}

    for b in range(n_boot):
        pick = rng.integers(0, n_patients, n_patients)          # patients with replacement
        idx = np.concatenate([groups[i] for i in pick])         # their images, dups allowed
        y_b = y_all[idx]
        if y_b.sum() == 0 or y_b.sum() == y_b.size:
            continue                                            # degenerate resample
        for c in prob_cols:
            p_b = probs[c][idx]
            for m in metrics:
                draws[c][m][b] = _metric_value(m, y_b, p_b, spec)

    lo_q, hi_q = 100 * alpha / 2, 100 * (1 - alpha / 2)
    out = {"n_boot": n_boot, "n_patients": n_patients, "metrics": list(metrics),
           "point": point, "ci": {}, "diff": {}}
    for c in prob_cols:
        out["ci"][c] = {
            m: (float(np.nanpercentile(draws[c][m], lo_q)),
                float(np.nanpercentile(draws[c][m], hi_q)))
            for m in metrics
        }

    # paired differences for every model pair
    for i, a in enumerate(prob_cols):
        for b_ in prob_cols[i + 1:]:
            out["diff"][f"{a} - {b_}"] = {}
            for m in metrics:
                d = draws[a][m] - draws[b_][m]
                out["diff"][f"{a} - {b_}"][m] = {
                    "delta": point[a][m] - point[b_][m],
                    "lo": float(np.nanpercentile(d, lo_q)),
                    "hi": float(np.nanpercentile(d, hi_q)),
                    "p_two_sided": float(
                        2 * min(np.nanmean(d <= 0), np.nanmean(d >= 0))
                    ),
                }
    return out


def to_frame(result: dict, metrics=None) -> pd.DataFrame:
    """Flatten the bootstrap result into the results table used in the report."""
    metrics = metrics or result.get("metrics") or DEFAULT_METRICS
    rows = []
    for model, vals in result["point"].items():
        for m in metrics:
            lo, hi = result["ci"][model][m]
            rows.append({
                "model": model, "metric": m, "point": vals[m],
                "ci_lo": lo, "ci_hi": hi,
                "ci_str": f"{vals[m]:.3f} [{lo:.3f}, {hi:.3f}]",
            })
    return pd.DataFrame(rows)
