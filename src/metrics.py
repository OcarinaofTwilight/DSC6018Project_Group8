"""Pure-numpy metrics for the ISIC-2020 calibration benchmark.

Every function takes (y, p) where y in {0,1} and p in [0,1] and returns a float.
No sklearn dependency: this module is the single source of truth for numbers that
appear in the report, and it is unit-tested in tests/test_metrics.py.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-12


# ----------------------------------------------------------------------------- helpers
def _as_arrays(y, p):
    y = np.asarray(y).astype(int).ravel()
    p = np.asarray(p, dtype=float).ravel()
    if y.shape != p.shape:
        raise ValueError(f"shape mismatch: {y.shape} vs {p.shape}")
    return y, p


def _logit(p, eps=1e-6):
    p = np.clip(p, eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


# ----------------------------------------------------------------------------- ranking
def auroc(y, p):
    """AUROC via the Mann-Whitney statistic with mid-ranks for ties."""
    y, p = _as_arrays(y, p)
    n_pos = int(y.sum())
    n_neg = int(y.size - n_pos)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(p, kind="mergesort")
    p_sorted = p[order]
    ranks_sorted = np.empty(p.size, dtype=float)
    i = 0
    while i < p.size:
        j = i
        while j + 1 < p.size and p_sorted[j + 1] == p_sorted[i]:
            j += 1
        ranks_sorted[i:j + 1] = 0.5 * (i + j) + 1.0
        i = j + 1
    ranks = np.empty(p.size, dtype=float)
    ranks[order] = ranks_sorted
    u = ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def auprc(y, p):
    """Average precision (step-interpolated PR curve, ties handled as one point)."""
    y, p = _as_arrays(y, p)
    n_pos = int(y.sum())
    if n_pos == 0:
        return float("nan")
    order = np.argsort(-p, kind="mergesort")
    p_s, y_s = p[order], y[order]
    tp = np.cumsum(y_s)
    fp = np.cumsum(1 - y_s)
    last_of_tie = np.r_[np.diff(p_s) != 0, True]
    tp, fp = tp[last_of_tie], fp[last_of_tie]
    prec = tp / np.maximum(tp + fp, EPS)
    rec = tp / tp[-1]
    d_rec = np.diff(np.r_[0.0, rec])
    return float(np.sum(d_rec * prec))


def partial_auroc(y, p, fpr_max=0.20):
    """Standardised partial AUROC over [0, fpr_max]; 1.0 is perfect in that region.

    Aligned with a triage use-case where only the high-specificity region matters.
    """
    y, p = _as_arrays(y, p)
    n_pos, n_neg = int(y.sum()), int(y.size - y.sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(-p, kind="mergesort")
    y_s = y[order]
    tpr = np.cumsum(y_s) / n_pos
    fpr = np.cumsum(1 - y_s) / n_neg
    fpr = np.r_[0.0, fpr]
    tpr = np.r_[0.0, tpr]
    keep = fpr <= fpr_max
    f, t = fpr[keep], tpr[keep]
    # add the interpolated crossing point so the region is fully covered
    if f[-1] < fpr_max:
        j = len(f) - 1
        if j + 1 < len(fpr):
            f_next, t_next = fpr[j + 1], tpr[j + 1]
            if f_next > f[j]:
                w = (fpr_max - f[j]) / (f_next - f[j])
                f = np.r_[f, fpr_max]
                t = np.r_[t, t[j] + w * (t_next - t[j])]
    area = np.trapz(t, f) if hasattr(np, "trapz") else np.trapezoid(t, f)
    return float(area / fpr_max)


# ----------------------------------------------------------------------------- proper scores
def brier(y, p):
    y, p = _as_arrays(y, p)
    return float(np.mean((p - y) ** 2))


def nll(y, p):
    y, p = _as_arrays(y, p)
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


# ----------------------------------------------------------------------------- calibration
def _bin_edges(p, bins, mode):
    if mode == "uniform":
        return np.linspace(0.0, 1.0, bins + 1)
    if mode == "quantile":
        e = np.quantile(p, np.linspace(0.0, 1.0, bins + 1))
        return np.unique(e)
    raise ValueError(f"unknown binning mode: {mode}")


def reliability_table(y, p, bins=15, mode="uniform"):
    """Return (count, mean_conf, frac_pos) per non-empty bin."""
    y, p = _as_arrays(y, p)
    edges = _bin_edges(p, bins, mode)
    idx = np.clip(np.digitize(p, edges[1:-1], right=False), 0, len(edges) - 2)
    rows = []
    for b in range(len(edges) - 1):
        m = idx == b
        n = int(m.sum())
        if n == 0:
            continue
        rows.append((n, float(p[m].mean()), float(y[m].mean())))
    return rows


def ece(y, p, bins=15, mode="uniform", subset="all"):
    """Expected calibration error.

    subset="all"  -> standard ECE over every image (dominated by the majority
                     class under 1.8% prevalence; report it, but never alone).
    subset="pos"  -> ECE computed only over true melanomas ("ECE_pos"), i.e. does
                     the model actually output high probabilities when the lesion
                     is malignant.
    """
    y, p = _as_arrays(y, p)
    if subset == "pos":
        y, p = y[y == 1], p[y == 1]
        if y.size == 0:
            return float("nan")
        edges = _bin_edges(p, bins, mode)
        idx = np.clip(np.digitize(p, edges[1:-1], right=False), 0, len(edges) - 2)
        total, val = 0.0, 0.0
        for b in range(len(edges) - 1):
            m = idx == b
            n = int(m.sum())
            if n == 0:
                continue
            val += n * abs(float(p[m].mean()) - 1.0)
            total += n
        return float(val / max(total, 1))
    rows = reliability_table(y, p, bins=bins, mode=mode)
    n_tot = sum(r[0] for r in rows)
    return float(sum(r[0] * abs(r[1] - r[2]) for r in rows) / max(n_tot, 1))


def brier_decomposition(y, p, bins=15, mode="quantile"):
    """Murphy decomposition: Brier = reliability - resolution + uncertainty.

    Exact only when the bins group identical scores; with continuous probabilities the
    residual is E[Var(p | bin)] and is reported only as an illustration.
    """
    y, p = _as_arrays(y, p)
    rows = reliability_table(y, p, bins=bins, mode=mode)
    n_tot = sum(r[0] for r in rows)
    base = float(y.mean())
    rel = sum(r[0] * (r[1] - r[2]) ** 2 for r in rows) / max(n_tot, 1)
    res = sum(r[0] * (r[2] - base) ** 2 for r in rows) / max(n_tot, 1)
    unc = base * (1 - base)
    return {"reliability": float(rel), "resolution": float(res), "uncertainty": float(unc)}


def calibration_slope(y, p, ridge=1e-6):
    """Fit logit(y) ~ a + b * logit(p) by IRLS.

    b < 1  => over-confident (probabilities spread too wide)
    b > 1  => under-confident.  a != 0 => systematic prior shift.
    """
    y, p = _as_arrays(y, p)
    z = _logit(p)
    X = np.column_stack([np.ones_like(z), z])
    beta = np.zeros(2)
    for _ in range(60):
        eta = X @ beta
        mu = 1.0 / (1.0 + np.exp(-np.clip(eta, -35, 35)))
        w = np.clip(mu * (1 - mu), 1e-8, None)
        H = X.T @ (X * w[:, None]) + ridge * np.eye(2)
        g = X.T @ (y - mu) - ridge * beta
        step = np.linalg.solve(H, g)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return float(beta[1]), float(beta[0])


def temperature_nll(y, logits):
    """Optimal temperature by 1-D grid search on NLL (post-hoc, fit on val only)."""
    y = np.asarray(y).astype(float).ravel()
    logits = np.asarray(logits, dtype=float).ravel()
    best_t, best = 1.0, np.inf
    for t in np.exp(np.linspace(np.log(0.05), np.log(20.0), 400)):
        z = logits / t
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))
        p = np.clip(p, 1e-7, 1 - 1e-7)
        v = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        if v < best:
            best, best_t = v, float(t)
    return best_t


def apply_temperature(p, t):
    """Rescale probabilities by one scalar: sigmoid(logit(p) / t).

    Strictly monotone, so AUROC / AUPRC / Sens@Spec are unchanged by construction --
    exactly why temperature scaling separates "the scale is broken" from "the ranking
    is broken".
    """
    p = np.clip(np.asarray(p, dtype=float).ravel(), 1e-6, 1 - 1e-6)
    z = _logit(p) / max(float(t), 1e-6)
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


# ----------------------------------------------------------------------------- operating point
def threshold_at_specificity(y, p, spec=0.80):
    """Score threshold whose benign tail leaves `spec` of negatives below it.

    Specificity = P(score < t | benign), so t is the `spec`-quantile of the benign
    scores (0.80 -> 80th percentile of negatives), NOT the 1-spec quantile.
    """
    y, p = _as_arrays(y, p)
    neg = p[y == 0]
    if neg.size == 0:
        return float("nan")
    return float(np.quantile(neg, spec))


def sens_at_spec(y, p, spec=0.80, threshold=None):
    """Sensitivity at a fixed specificity, plus the specificity actually achieved."""
    y, p = _as_arrays(y, p)
    thr = threshold_at_specificity(y, p, spec) if threshold is None else float(threshold)
    pred = p >= thr
    n_pos, n_neg = int(y.sum()), int(y.size - y.sum())
    sens = float(pred[y == 1].mean()) if n_pos else float("nan")
    achieved = float((~pred[y == 0]).mean()) if n_neg else float("nan")
    return sens, achieved, thr


def net_benefit(y, p, thresholds=None):
    """Decision-curve net benefit for a 'refer to dermatology' rule."""
    y, p = _as_arrays(y, p)
    if thresholds is None:
        thresholds = np.linspace(0.01, 0.50, 50)
    n = y.size
    out = []
    for pt in thresholds:
        pred = p >= pt
        tp = np.sum(pred & (y == 1))
        fp = np.sum(pred & (y == 0))
        nb = tp / n - fp / n * (pt / (1 - pt))
        out.append(float(nb))
    return np.asarray(thresholds), np.asarray(out)


# ----------------------------------------------------------------------------- report bundle
def summary(y, p, spec=0.80, bins=15, thr=None, with_slope=False):
    """The exact metric dict that goes into results.csv."""
    y, p = _as_arrays(y, p)
    sens, achieved, t = sens_at_spec(y, p, spec=spec, threshold=thr)
    d = {
        "n": int(y.size),
        "n_pos": int(y.sum()),
        "prevalence": float(y.mean()),
        "auroc": auroc(y, p),
        "auprc": auprc(y, p),
        "pauc_fpr20": partial_auroc(y, p, 0.20),
        "brier": brier(y, p),
        "nll": nll(y, p),
        "ece_uniform15": ece(y, p, bins=bins, mode="uniform"),
        "ece_adaptive15": ece(y, p, bins=bins, mode="quantile"),
        "ece_pos": ece(y, p, bins=bins, mode="quantile", subset="pos"),
        f"sens_at_spec{int(round(spec * 100))}": sens,
        "spec_achieved": achieved,
        "threshold": t,
    }
    if with_slope:
        s, i = calibration_slope(y, p)
        d["cal_slope"], d["cal_intercept"] = s, i
    return d
