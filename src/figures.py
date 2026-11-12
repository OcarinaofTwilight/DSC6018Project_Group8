"""The four figures the report needs, plus the reliability diagram with bootstrap band.

    python src/figures.py --preds runs/*/test_preds.csv --out-dir figures/

Every function takes a dict {label: DataFrame} where each frame has `target` and
`prob`. Nothing here touches the model, so figures can be regenerated from the saved
prediction CSVs without a GPU -- which is exactly what you want when the report
deadline is close and Colab is out of quota.
"""
from __future__ import annotations

import argparse
import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from metrics import net_benefit, reliability_table, summary

PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]


def _style(ax, xlabel, ylabel, title=None):
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    if title:
        ax.set_title(title, fontsize=10)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.3, linewidth=0.5)


def reliability_diagram(preds: dict, ax=None, bins=10, mode="quantile"):
    ax = ax or plt.gca()
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, label="perfect")
    for k, (name, df) in enumerate(preds.items()):
        rows = reliability_table(df["target"].to_numpy(), df["prob"].to_numpy(),
                                 bins=bins, mode=mode)
        conf = [r[1] for r in rows]
        freq = [r[2] for r in rows]
        ax.plot(conf, freq, "o-", markersize=3, linewidth=1.2,
                color=PALETTE[k % len(PALETTE)], label=name)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    _style(ax, "predicted probability", "observed melanoma rate",
           f"Reliability diagram ({mode} bins, n={bins})")
    ax.legend(fontsize=7, loc="upper left")


def roc_curve(preds: dict, ax=None):
    ax = ax or plt.gca()
    for k, (name, df) in enumerate(preds.items()):
        y = df["target"].to_numpy()
        p = df["prob"].to_numpy()
        order = np.argsort(-p)
        y_s = y[order]
        n_pos, n_neg = y.sum(), y.size - y.sum()
        tpr = np.r_[0, np.cumsum(y_s) / n_pos]
        fpr = np.r_[0, np.cumsum(1 - y_s) / n_neg]
        a = summary(y, p)["auroc"]
        ax.plot(fpr, tpr, linewidth=1.2, color=PALETTE[k % len(PALETTE)],
                label=f"{name} (AUROC {a:.3f})")
    ax.plot([0, 1], [0, 1], "k:", linewidth=0.7)
    ax.axvline(0.20, color="grey", linestyle="--", linewidth=0.8)
    _style(ax, "false positive rate (1 - specificity)", "sensitivity", "ROC")
    ax.legend(fontsize=7, loc="lower right")


def sensitivity_specificity_curve(preds: dict, ax=None, target_spec=0.80):
    """The figure that makes the triage trade-off legible in one glance."""
    ax = ax or plt.gca()
    specs = np.linspace(0.50, 0.99, 60)
    for k, (name, df) in enumerate(preds.items()):
        y = df["target"].to_numpy()
        p = df["prob"].to_numpy()
        neg = np.sort(p[y == 0])
        sens = [float((p[y == 1] >= np.quantile(neg, s)).mean()) for s in specs]
        ax.plot(specs, sens, linewidth=1.2, color=PALETTE[k % len(PALETTE)], label=name)
        pt = summary(y, p)["sens_at_spec80"]
        ax.scatter([target_spec], [pt], color=PALETTE[k % len(PALETTE)], s=18, zorder=5)
    ax.axvline(target_spec, color="grey", linestyle="--", linewidth=0.8)
    _style(ax, "specificity", "sensitivity", "Sensitivity vs specificity")
    ax.legend(fontsize=7, loc="upper left")


def decision_curve(preds: dict, ax=None, prevalence=None):
    ax = ax or plt.gca()
    first = next(iter(preds.values()))
    prev = prevalence if prevalence is not None else float(first["target"].mean())
    thr = np.linspace(0.005, 0.40, 80)
    for k, (name, df) in enumerate(preds.items()):
        t, nb = net_benefit(df["target"].to_numpy(), df["prob"].to_numpy(), thr)
        ax.plot(t, nb, linewidth=1.2, color=PALETTE[k % len(PALETTE)], label=name)
    ax.plot(thr, prev - (1 - prev) * thr / (1 - thr), "k:", linewidth=0.8, label="treat all")
    ax.axhline(0, color="grey", linewidth=0.6)
    ax.set_ylim(-0.02, max(prev * 1.15, 0.05))
    _style(ax, "threshold probability", "net benefit", "Decision curve (refer to dermatology)")
    ax.legend(fontsize=7)


def make_panel(preds: dict, out_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 8.0))
    reliability_diagram(preds, axes[0, 0])
    roc_curve(preds, axes[0, 1])
    sensitivity_specificity_curve(preds, axes[1, 0])
    decision_curve(preds, axes[1, 1], prevalence=0.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"saved {out_path}")


def load(paths):
    preds = {}
    for p in paths:
        name = os.path.basename(os.path.dirname(os.path.normpath(p)))
        preds[name] = pd.read_csv(p)
    return preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", nargs="+", required=True, help="test_preds.csv paths")
    ap.add_argument("--out-dir", default="figures")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    paths = []
    for pat in args.preds:
        paths.extend(sorted(glob.glob(pat)) or [pat])
    preds = load(paths)
    make_panel(preds, os.path.join(args.out_dir, "panel.png"))
    for name, df in preds.items():
        s = summary(df["target"].to_numpy(), df["prob"].to_numpy(), with_slope=True)
        print(name, {k: round(v, 4) for k, v in s.items() if isinstance(v, float)})


if __name__ == "__main__":
    main()
