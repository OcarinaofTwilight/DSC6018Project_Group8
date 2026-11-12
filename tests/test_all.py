"""Self-tests that run on CPU with numpy only -- no torch, no dataset, no GPU.

    python tests/test_all.py

These cover the parts that silently produce wrong numbers in a report: the metric
implementations, the patient-disjoint splitter, and the bootstrap.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import metrics as M          # noqa: E402
import split as S            # noqa: E402
import bootstrap as B        # noqa: E402

rng = np.random.default_rng(0)
FAIL = []


def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        FAIL.append(name)


# ---------------------------------------------------------------- AUROC
y = np.array([0, 0, 1, 1])
p = np.array([0.1, 0.2, 0.8, 0.9])
check("auroc perfect separation == 1.0", abs(M.auroc(y, p) - 1.0) < 1e-12, f"{M.auroc(y, p):.4f}")
check("auroc reversed == 0.0", abs(M.auroc(y, -p) - 0.0) < 1e-12)
check("auroc all-ties == 0.5", abs(M.auroc(y, np.ones(4)) - 0.5) < 1e-12)
# one tie pair: pos {0.5, 0.9}, neg {0.1, 0.5}
#   pos 0.5 -> 1 neg below + 0.5 * 1 neg tied = 1.5 ; pos 0.9 -> 2 ; U = 3.5 / 4 = 0.875
yt = np.array([1, 1, 0, 0])
pt = np.array([0.5, 0.9, 0.1, 0.5])
check("auroc tie handling", abs(M.auroc(yt, pt) - 0.875) < 1e-12, f"{M.auroc(yt, pt):.4f}")

# ---------------------------------------------------------------- AUPRC
check("auprc perfect == 1.0", abs(M.auprc(y, p) - 1.0) < 1e-12)
check("auprc random-ish < 1", M.auprc(y, np.array([0.6, 0.4, 0.55, 0.5])) < 1.0)
# prevalence baseline: constant score -> AP == prevalence
yc = rng.random(5000) < 0.02
check("auprc constant == prevalence",
      abs(M.auprc(yc, np.full(5000, 0.3)) - yc.mean()) < 1e-3, f"{yc.mean():.4f}")

# ---------------------------------------------------------------- ECE / Brier
n = 200_000
p_true = rng.beta(0.7, 12.0, n)                       # sharp, low probabilities
y_sim = (rng.random(n) < p_true).astype(int)
check("ece ~0 for calibrated model", M.ece(y_sim, p_true, bins=20, mode="quantile") < 0.01,
      f"{M.ece(y_sim, p_true, bins=20, mode='quantile'):.4f}")
check("ece == |p - prevalence| for constant forecast",
      abs(M.ece(y_sim, np.full(n, 0.5)) - abs(0.5 - y_sim.mean())) < 1e-6)
# The Murphy decomposition is exact only when every bin holds a single probability,
# so the identity is checked on a discrete forecast with one value per uniform bin.
p_disc = np.repeat(np.array([0.01, 0.06, 0.21, 0.61, 0.91]), 20_000)
y_disc = (rng.random(p_disc.size) < p_disc).astype(int)
bd = M.brier_decomposition(y_disc, p_disc, bins=20, mode="uniform")
resid = (bd["reliability"] - bd["resolution"] + bd["uncertainty"]) - M.brier(y_disc, p_disc)
check("brier decomposition rel - res + unc == brier (discrete forecast)",
      abs(resid) < 1e-9, f"resid={resid:.2e}")

# ece_pos: perfect model on positives gives ~0; a model that outputs 0.5 for a true
# melanoma is penalised by |0.5 - 1| = 0.5
check("ece_pos penalises under-confident positives",
      abs(M.ece(y, np.array([0.1, 0.1, 0.5, 0.5]), subset="pos") - 0.5) < 1e-12,
      f"{M.ece(y, np.array([0.1, 0.1, 0.5, 0.5]), subset='pos'):.3f}")

# ---------------------------------------------------------------- operating point
# 100 negatives with scores 0..0.99, 10 positives all above 0.9 -> spec 0.8 -> thr=0.79
neg = np.linspace(0, 0.99, 100)
pos = np.linspace(0.90, 0.99, 10)
yy = np.r_[np.zeros(100), np.ones(10)]
pp = np.r_[neg, pos]
sens, spec, thr = M.sens_at_spec(yy, pp, spec=0.80)
check("sens@spec80 threshold lands on the negative quantile", abs(thr - 0.79) < 0.02, f"thr={thr:.3f}")
check("sens@spec80 == 1.0 here", abs(sens - 1.0) < 1e-12, f"sens={sens:.3f}")
check("achieved specificity is reported", 0.78 <= spec <= 0.82, f"spec={spec:.3f}")

# ---------------------------------------------------------------- calibration slope
z = rng.normal(0, 1.2, 40_000)
p_cal = 1 / (1 + np.exp(-z))
y_cal = (rng.random(z.size) < p_cal).astype(int)
s_cal, i_cal = M.calibration_slope(y_cal, p_cal)
check("calibration slope ~1 for calibrated probabilities", abs(s_cal - 1.0) < 0.08, f"slope={s_cal:.3f}")
# over-confident: sharpen the same probabilities -> slope < 1
p_sharp = 1 / (1 + np.exp(-3.0 * z))
y_sharp = (rng.random(z.size) < p_cal).astype(int)
s_sharp, _ = M.calibration_slope(y_sharp, p_sharp)
check("over-confident probabilities give slope < 1", s_sharp < 0.6, f"slope={s_sharp:.3f}")

# ---------------------------------------------------------------- temperature
logits = z
T = M.temperature_nll(y_cal, 3.0 * logits)             # 3x sharpened -> optimal T ~ 3
check("temperature recovers the sharpening factor", 2.2 < T < 4.2, f"T={T:.2f}")

# ---------------------------------------------------------------- split
rng2 = np.random.default_rng(7)
n_pat = 2056
sizes = rng2.integers(1, 6, n_pat).astype(int)
sizes[0] = 800                                          # one very large patient
n_img = int(sizes.sum())
patient_ids = [f"IP_{i:06d}" for i in range(n_pat)]
mel_pat = rng2.choice(n_pat, size=190, replace=False)   # melanomas concentrate by patient
targets, pids, lesion = [], [], []
for i, s in enumerate(sizes):
    for k in range(s):
        pids.append(patient_ids[i])
        lesion.append(f"IL_{i:06d}_{k}")
        targets.append(1 if (i in mel_pat and k == 0) else 0)
df = pd.DataFrame({"image_name": [f"ISIC_{i:07d}" for i in range(n_img)],
                   "patient_id": pids, "lesion_id": lesion, "target": targets})
man = S.build_manifest(df, seed=42)
rep = S.validate(man, verbose=False)

tr = rep["train"]["images"] / n_img
te = rep["test"]["images"] / n_img
check("split sizes close to 70/10/20", abs(tr - 0.70) < 0.02 and abs(te - 0.20) < 0.02,
      f"train={tr:.3f} test={te:.3f}")
prev = df["target"].mean()
# a 15%-sized hold-out has ~1200 images, so sampling noise on prevalence is real:
# require every split to sit inside 3 binomial sigma of the global rate.
def within(split):
    n_s = rep[split]["images"]
    sd = (prev * (1 - prev) / n_s) ** 0.5
    return abs(rep[split]["prevalence"] - prev) <= 3 * sd + 1e-4

check("prevalence preserved in every split (3 sigma)",
      all(within(s) for s in ("train", "val", "test")),
      f"global={prev:.4f} " + " ".join(f"{s}={rep[s]['prevalence']:.4f}" for s in ("train", "val", "test")))
# determinism
man2 = S.build_manifest(df, seed=42)
check("same seed -> identical manifest", (man["split"].values == man2["split"].values).all())
man3 = S.build_manifest(df, seed=43)
check("different seed -> different manifest", (man["split"].values != man3["split"].values).any())
# the big patient must not be split
big = man[man.patient_id == patient_ids[0]]["split"].nunique()
check("a single patient lives in exactly one split", big == 1)

# ---------------------------------------------------------------- bootstrap
pred = man[["patient_id", "target"]].copy()
for k, name in enumerate(["bce", "wbce", "focal"]):
    zz = rng2.normal(0, 1, len(pred)) + pred["target"].to_numpy() * (2.0 - 0.4 * k)
    pred[name] = 1 / (1 + np.exp(-zz))
res = B.patient_bootstrap(pred, ["bce", "wbce", "focal"], n_boot=200, seed=1,
                          metrics=("auroc", "auprc", "sens_at_spec80", "ece_adaptive15"))
ok_ci = all(res["ci"][m]["auroc"][0] <= res["point"][m]["auroc"] <= res["ci"][m]["auroc"][1]
            for m in ["bce", "wbce", "focal"])
check("bootstrap CI contains the point estimate", ok_ci)
tbl = B.to_frame(res)
check("bootstrap table has 3 models x 4 metrics", len(tbl) == 12)
d = res["diff"]["bce - focal"]["auroc"]
check("paired difference CI is ordered", d["lo"] < d["delta"] < d["hi"],
      f"{d['delta']:.3f} [{d['lo']:.3f}, {d['hi']:.3f}]")

print()
if FAIL:
    print(f"{len(FAIL)} FAILED: {FAIL}")
    sys.exit(1)
print("all checks passed")
