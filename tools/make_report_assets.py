"""Regenerate the two report figures from the saved prediction CSVs.

    <venv>\\Scripts\\python.exe tools\\make_report_assets.py

Writes report_assets/fig_calibration.png and report_assets/fig_errors.png at 300 dpi.
Pure matplotlib on top of the CSVs in runs/, so it needs no GPU and no retraining.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "report_assets")
RUNS = ["b3_bce", "b3_wbce", "b3_focal", "r50_bce", "b3_bce_meta"]
LABEL = {"b3_bce": "B3 + BCE", "b3_wbce": "B3 + inv-prev BCE", "b3_focal": "B3 + focal",
         "r50_bce": "R50 + BCE", "b3_bce_meta": "B3 + BCE + metadata"}
C = {"b3_bce": "#1f77b4", "b3_wbce": "#9467bd", "b3_focal": "#2ca02c",
     "r50_bce": "#ff7f0e", "b3_bce_meta": "#d62728"}

plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False})


def load(run, split="test"):
    return pd.read_csv(os.path.join(ROOT, "runs", run, f"{split}_preds.csv"))


def fig_calibration():
    ece_b, ece_a, temps = [], [], []
    for r in RUNS:
        j = json.load(open(os.path.join(ROOT, "runs", r, "temperature.json")))
        ece_b.append(j["before"]["ece_adaptive15"])
        ece_a.append(j["after"]["ece_adaptive15"])
        temps.append(j["T"])

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    x = np.arange(len(RUNS))
    ax.bar(x - 0.19, ece_b, 0.38, color=[C[r] for r in RUNS], alpha=0.95, label="before scaling")
    ax.bar(x + 0.19, ece_a, 0.38, color=[C[r] for r in RUNS], alpha=0.45, hatch="//",
           edgecolor="white", label="after temperature scaling")
    for i, (b, a, t) in enumerate(zip(ece_b, ece_a, temps)):
        ax.text(i - 0.19, b + 0.004, f"{b:.3f}", ha="center", va="bottom", fontsize=6.8)
        if abs(a - b) / max(b, 1e-9) > 0.15:
            ax.text(i + 0.19, a + 0.004, f"{a:.3f}", ha="center", va="bottom", fontsize=6.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{n}\nT={t:.2f}" for n, t in zip(["BCE", "inv-prev", "focal", "R50 BCE", "BCE+meta"], temps)], fontsize=6.8)
    ax.set_ylabel("ECE (adaptive, 15 bins)")
    ax.set_title("Calibration damage and what one scalar can undo", fontsize=9)
    ax.set_ylim(0, max(ece_b) * 1.22)
    ax.legend(fontsize=7, frameon=False, loc="upper right")

    # right: reliability curves, log x, to show the low-probability region where 1.8% lives
    ax = axes[1]
    for r in RUNS:
        te = load(r)
        order = np.argsort(te.prob.values)
        p = te.prob.values[order]
        y = te.target.values[order]
        edges = np.quantile(p, np.linspace(0, 1, 11))
        edges = np.unique(edges)
        idx = np.clip(np.digitize(p, edges[1:-1]), 0, len(edges) - 2)
        conf, freq = [], []
        for b in range(len(edges) - 1):
            m = idx == b
            if m.sum() >= 20 and y[m].mean() > 0:
                conf.append(p[m].mean())
                freq.append(y[m].mean())
        ax.plot(conf, freq, "o-", ms=2.6, lw=1.1, color=C[r], label=LABEL[r])
    ax.plot([1e-5, 1], [1e-5, 1], "k--", lw=0.7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e-5, 0.6)
    ax.set_ylim(1e-4, 0.6)
    ax.set_xlabel("predicted probability (log)")
    ax.set_ylabel("observed melanoma rate (log)")
    ax.set_title("Reliability in the region that matters", fontsize=9)
    ax.legend(fontsize=6.4, frameon=False, loc="upper left")

    fig.tight_layout()
    out = os.path.join(ASSETS, "fig_calibration.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print("saved", out)


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def fig_errors():
    man = pd.read_csv(os.path.join(ROOT, "manifests", "split_seed42.csv"))
    te = load("b3_bce").merge(
        man[["image_name", "age_approx", "anatom_site_general_challenge"]], on="image_name")
    thr = 0.016951          # val-selected threshold for b3_bce (see Table 1)
    te["pred"] = (te.prob >= thr).astype(int)
    pos = te[te.target == 1].copy()
    pos["miss"] = pos.pred == 0

    plt.rcParams.update({"font.size": 11, "xtick.labelsize": 10, "ytick.labelsize": 10})
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.5),
                             gridspec_kw={"width_ratios": [1.25, 1, 1]})

    ax = axes[0]
    bins = np.logspace(-4.2, 0.2, 26)
    ax.hist(pos.loc[~pos.miss, "prob"], bins=bins, color="#1f77b4", alpha=0.75,
            label=f"detected (n={int((~pos.miss).sum())})")
    ax.hist(pos.loc[pos.miss, "prob"], bins=bins, color="#d62728", alpha=0.75,
            label=f"missed (n={int(pos.miss.sum())})")
    ax.axvline(thr, color="k", ls="--", lw=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("predicted probability (log)")
    ax.set_ylabel("melanoma images")
    ax.set_title("Misses are confident, not borderline", fontsize=11)
    ax.legend(fontsize=7, frameon=True, facecolor="white", edgecolor="none", framealpha=1.0)

    ax = axes[1]
    pos["band"] = pd.cut(pos.age_approx, [0, 40, 55, 70, 200],
                         labels=["≤40", "41–55", "56–70", ">70"])
    rows = []
    for b in ["≤40", "41–55", "56–70", ">70"]:
        sub = pos[pos.band == b]
        if len(sub):
            lo, hi = wilson(int(sub.miss.sum()), len(sub))
            rows.append((b, len(sub), sub.miss.mean(), lo, hi))
    ax.bar(range(len(rows)), [r[2] for r in rows], color="#4c72b0", width=0.62)
    ax.errorbar(range(len(rows)), [r[2] for r in rows],
                yerr=[[r[2] - r[3] for r in rows], [r[4] - r[2] for r in rows]],
                fmt="none", ecolor="k", lw=0.9, capsize=2.5)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([f"{r[0]}  {int(round(r[2]*r[1]))}/{r[1]}" for r in rows], fontsize=9, rotation=32, ha="right")
    ax.set_ylabel("miss rate (95% Wilson CI)")
    ax.set_title("By age band", fontsize=11)
    ax.set_ylim(0, 0.75)

    ax = axes[2]
    site = pos.anatom_site_general_challenge.fillna("unknown")
    keep = [s for s in ["torso", "lower extremity", "upper extremity", "head/neck"]
            if (site == s).sum() >= 10]
    rows = []
    for s in keep:
        sub = pos[site == s]
        lo, hi = wilson(int(sub.miss.sum()), len(sub))
        rows.append(({"lower extremity": "lower\nextr.", "upper extremity": "upper\nextr.",
                      "head/neck": "head/\nneck"}.get(s, s), len(sub), sub.miss.mean(), lo, hi))
    ax.bar(range(len(rows)), [r[2] for r in rows], color="#55a868", width=0.62)
    ax.errorbar(range(len(rows)), [r[2] for r in rows],
                yerr=[[r[2] - r[3] for r in rows], [r[4] - r[2] for r in rows]],
                fmt="none", ecolor="k", lw=0.9, capsize=2.5)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([f"{r[0]}  {int(round(r[2]*r[1]))}/{r[1]}" for r in rows], fontsize=9, rotation=32, ha="right")
    ax.set_ylabel("miss rate (95% Wilson CI)")
    ax.set_title("By anatomical site", fontsize=11)
    ax.set_ylim(0, 0.75)

    fig.tight_layout()
    out = os.path.join(ASSETS, "fig_errors.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print("saved", out)



def fig_training():
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.4), sharex=True)
    for r in RUNS:
        log = pd.read_csv(os.path.join(ROOT, "runs", r, "log.csv"))
        axes[0].plot(log.epoch, log.val_auroc, "o-", ms=2.2, lw=1.0, color=C[r], label=LABEL[r])
        axes[1].plot(log.epoch, log.val_auprc, "o-", ms=2.2, lw=1.0, color=C[r])
    axes[0].set_xlabel("epoch")
    axes[1].set_xlabel("epoch")
    axes[0].set_ylabel("validation AUROC")
    axes[1].set_ylabel("validation AUPRC")
    axes[0].set_title("Ranking", fontsize=9)
    axes[1].set_title("AUPRC is the noisier selection signal (58 val positives)", fontsize=8)
    axes[0].legend(fontsize=6.4, frameon=False, loc="lower right")
    axes[0].set_ylim(0.65, 0.92)
    fig.tight_layout()
    out = os.path.join(ASSETS, "fig_training.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print("saved", out)

def fig_decision():
    """Single decision-curve panel for the talk (the 2x2 panel is too small on a slide)."""
    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    thr = np.linspace(0.005, 0.40, 120)
    prev = float(load("b3_bce").target.mean())
    for r in RUNS:
        te = load(r)
        n = te.target.size
        nb = []
        for t in thr:
            pred = te.prob.values >= t
            nb.append((pred & (te.target.values == 1)).sum() / n
                      - (pred & (te.target.values == 0)).sum() / n * t / (1 - t))
        ax.plot(thr, nb, lw=1.8, color=C[r], label=LABEL[r])
    ax.plot(thr, prev - (1 - prev) * thr / (1 - thr), "k:", lw=1.0, label="treat all")
    ax.axhline(0, color="grey", lw=0.8, label="treat none")
    ax.set_xlim(0, 0.25)
    ax.set_ylim(-0.008, 0.014)
    ax.set_xlabel("referral threshold $p_t$")
    ax.set_ylabel("net benefit")
    ax.set_title("Decision curve: refer to dermatology", fontsize=10)
    ax.legend(fontsize=7.5, frameon=False, loc="upper right")
    fig.tight_layout()
    out = os.path.join(ASSETS, "fig_decision.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print("saved", out)
if __name__ == "__main__":
    os.makedirs(ASSETS, exist_ok=True)
    fig_calibration()
    fig_errors()
    fig_training()
    fig_decision()
