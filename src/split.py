"""Patient-disjoint splitting for ISIC 2020 (no sklearn dependency).

Why this file exists: the cheapest way to get a wrong answer on this dataset is to
split by image. Multiple images -- and multiple lesions -- belong to the same patient,
so an image-level split leaks patient identity into the test set and inflates every
metric. Everything downstream trusts this manifest, so the manifest is frozen, hashed
and validated before any GPU time is spent.

The splitter is a deterministic greedy balancer: patients are visited in a seeded
random order and each is dropped into the split with the largest *relative* deficit in
both image count and melanoma count. That keeps (a) patients disjoint, (b) the 1.76 %
prevalence approximately equal across splits, and (c) the result exactly reproducible
from the seed -- which `StratifiedGroupKFold` alone does not give you at arbitrary
ratios, and `GroupShuffleSplit` does not give you at all.

Usage
-----
    python src/split.py --csv data/train.csv --out manifests/split_seed42.csv
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

import numpy as np
import pandas as pd

GROUP_COL = "patient_id"
LABEL_COL = "target"

# 70 / 10 / 20. The test fraction is deliberately the largest of the two hold-outs:
# every headline number (Sens@Spec80, ECE) is estimated on test, and with 584
# melanomas in total the test positives are the binding constraint on precision.
DEFAULT_RATIOS = {"train": 0.70, "val": 0.10, "test": 0.20}


def _patient_stats(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(GROUP_COL)
    return pd.DataFrame({
        "n_img": g.size(),
        "n_pos": g[LABEL_COL].sum(),
        "n_lesion": g["lesion_id"].nunique() if "lesion_id" in df.columns else g.size(),
    }).reset_index()


def _assign(stats: pd.DataFrame, ratios: dict, seed: int, index_name="fold",
            repair_iters: int = 6000) -> pd.Series:
    """Greedy largest-relative-deficit assignment, then a swap-repair pass.

    Stage 1 (greedy) visits patients in a seeded random order and drops each one into
    the split with the largest *relative* deficit in images and in melanomas. It is
    fast and keeps patients disjoint, but it is myopic: because melanoma labels are
    concentrated in a few patients and image counts are heavy-tailed, the final
    prevalence can drift several tens of percent (e.g. 0.6 % in test instead of 1.76 %).

    Stage 2 (repair) hill-climbs on the split composition: it repeatedly tries to move
    one patient to another split, or to exchange a patient between two splits, and
    keeps a change only if the objective

        sum_s ( (imgs_s - tgt_imgs_s)/tgt_imgs_s )^2 + ( (pos_s - tgt_pos_s)/tgt_pos_s )^2

    decreases. Both stages consume the same seeded RNG, so the manifest is still an
    exact function of (data, seed).
    """
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(stats))
    stats = stats.iloc[order].reset_index(drop=True)

    names = list(ratios)
    n_split = len(names)
    totals = np.array([ratios[n] for n in names], dtype=float)
    tot_img = float(stats["n_img"].sum())
    tot_pos = max(float(stats["n_pos"].sum()), 1.0)
    tgt_img = totals / totals.sum() * tot_img
    tgt_pos = totals / totals.sum() * tot_pos
    # a split that is allowed to be empty would make tgt_pos 0 and the objective NaN
    tgt_pos = np.maximum(tgt_pos, 1e-9)
    tgt_img = np.maximum(tgt_img, 1e-9)

    cur_img = np.zeros(n_split)
    cur_pos = np.zeros(n_split)
    which = np.zeros(len(stats), dtype=int)

    for i, row in stats.iterrows():
        deficit = (tgt_img - cur_img) / tgt_img + (tgt_pos - cur_pos) / tgt_pos
        j = int(np.argmax(deficit))          # ties -> lowest index: deterministic
        which[i] = j
        cur_img[j] += row["n_img"]
        cur_pos[j] += row["n_pos"]

    img = stats["n_img"].to_numpy(dtype=float)
    pos = stats["n_pos"].to_numpy(dtype=float)

    def objective(_img, _pos):
        di = (_img - tgt_img) / tgt_img
        dp = (_pos - tgt_pos) / tgt_pos
        return float(np.sum(di * di + dp * dp))

    best_obj = objective(cur_img, cur_pos)
    if repair_iters > 0 and n_split > 1:
        for _ in range(repair_iters):
            i = int(rng.integers(0, len(stats)))
            a = which[i]
            b = int(rng.integers(0, n_split - 1))
            b = b + 1 if b >= a else b          # b != a
            if rng.random() < 0.5:
                # single-patient move a -> b
                ni = cur_img.copy()
                np_ = cur_pos.copy()
                ni[a] -= img[i]
                ni[b] += img[i]
                np_[a] -= pos[i]
                np_[b] += pos[i]
                cand = objective(ni, np_)
                if cand < best_obj - 1e-12:
                    which[i], cur_img, cur_pos, best_obj = b, ni, np_, cand
            else:
                # exchange one patient from a with one from b
                in_a = np.flatnonzero(which == a)
                in_b = np.flatnonzero(which == b)
                if in_a.size == 0 or in_b.size == 0:
                    continue
                j = int(in_b[rng.integers(0, in_b.size)])
                k = int(in_a[rng.integers(0, in_a.size)])
                ni = cur_img.copy()
                np_ = cur_pos.copy()
                ni[a] += img[j] - img[k]
                ni[b] += img[k] - img[j]
                np_[a] += pos[j] - pos[k]
                np_[b] += pos[k] - pos[j]
                cand = objective(ni, np_)
                if cand < best_obj - 1e-12:
                    which[j], which[k] = a, b
                    cur_img, cur_pos, best_obj = ni, np_, cand

    # no patient may end up in an empty split
    for j in range(n_split):
        if not np.any(which == j):
            which[int(np.argmax(img))] = j

    out = pd.Series([names[j] for j in which], index=stats[GROUP_COL])
    return out


def build_manifest(df: pd.DataFrame, seed: int = 42, ratios=None) -> pd.DataFrame:
    ratios = dict(ratios or DEFAULT_RATIOS)
    assert abs(sum(ratios.values()) - 1.0) < 1e-9, "ratios must sum to 1"

    df = df.copy()
    if LABEL_COL not in df.columns:
        raise KeyError(f"missing label column {LABEL_COL!r}")
    if GROUP_COL not in df.columns:
        raise KeyError(f"missing group column {GROUP_COL!r}")
    df[LABEL_COL] = df[LABEL_COL].astype(int)

    # Rows with no patient_id cannot be grouped; give each its own pseudo-patient so
    # they can never straddle two splits.
    missing = df[GROUP_COL].isna()
    if missing.any():
        df.loc[missing, GROUP_COL] = [f"UNK_{i}" for i in df.index[missing]]

    stats = _patient_stats(df)
    mapping = _assign(stats, ratios, seed=seed)
    df["split"] = df[GROUP_COL].map(mapping)
    return df


def make_cv_folds(df: pd.DataFrame, n_splits: int = 5, seed: int = 42) -> pd.Series:
    """Grouped CV assignment (patient -> fold) for the stability check, not for test."""
    names = [f"f{k}" for k in range(n_splits)]
    ratios = {n: 1.0 / n_splits for n in names}
    stats = _patient_stats(df)
    fold = _assign(stats, ratios, seed=seed)
    return df[GROUP_COL].map(fold)


def validate(df: pd.DataFrame, verbose: bool = True) -> dict:
    """Hard assertions + summary table. Run before every training job and quote it."""
    report = {}
    for split in ["train", "val", "test"]:
        sub = df[df["split"] == split]
        report[split] = {
            "images": int(len(sub)),
            "patients": int(sub[GROUP_COL].nunique()),
            "melanomas": int(sub[LABEL_COL].sum()),
            "prevalence": round(float(sub[LABEL_COL].mean()), 4) if len(sub) else float("nan"),
        }
        assert len(sub) > 0, f"empty split {split}"

    sets = {s: set(df.loc[df.split == s, GROUP_COL]) for s in ["train", "val", "test"]}
    assert not (sets["train"] & sets["val"]), "patient overlap train/val"
    assert not (sets["train"] & sets["test"]), "patient overlap train/test"
    assert not (sets["val"] & sets["test"]), "patient overlap val/test"
    assert df["split"].isin(["train", "val", "test"]).all(), "unassigned rows"

    if "lesion_id" in df.columns:
        spanning = int(df.groupby("lesion_id")["split"].nunique().gt(1).sum())
        report["lesions_spanning_splits"] = spanning
        assert spanning == 0, "a lesion appears in more than one split"

    dup = int(df["image_name"].duplicated().sum())
    report["duplicate_image_names"] = dup
    assert dup == 0, "duplicate image_name rows"

    # Prevalence cannot be *equal* across splits once the unit of assignment is a
    # patient with an arbitrary number of images: hitting an exact positive count would
    # mean breaking patients apart. Report the relative deviation and only warn, so the
    # number ends up in the report instead of being "fixed" by re-splitting.
    global_prev = float(df[LABEL_COL].mean())
    report["prevalence_global"] = round(global_prev, 4)
    dev = {}
    for split in ["train", "val", "test"]:
        p = report[split]["prevalence"]
        dev[split] = round(float((p - global_prev) / global_prev), 4) if global_prev else 0.0
    report["prevalence_rel_dev"] = dev
    warn = {k: v for k, v in dev.items() if abs(v) > 0.25}
    if warn:
        print("[warn] prevalence deviates >25% from the global rate in "
              f"{warn} -- quote these numbers instead of re-splitting")

    if verbose:
        rows = {s: report[s] for s in ["train", "val", "test"]}
        print(pd.DataFrame(rows).T.to_string())
        print("prevalence rel. dev: " + "  ".join(
            f"{s} {100 * v:+.1f}%" for s, v in dev.items()))
        print(f"lesions spanning splits: {report.get('lesions_spanning_splits', 0)}   "
              f"duplicate image names: {report['duplicate_image_names']}")
    return report


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/train.csv")
    ap.add_argument("--out", default="manifests/split_seed42.csv")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cv-folds", type=int, default=0, help="also write grouped CV folds")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    keep = [c for c in ["image_name", GROUP_COL, "lesion_id", LABEL_COL, "benign_malignant",
                        "age_approx", "sex", "anatom_site_general_challenge"] if c in df.columns]
    manifest = build_manifest(df[keep], seed=args.seed)
    report = validate(manifest)
    if args.cv_folds:
        manifest["cv_fold"] = make_cv_folds(manifest, args.cv_folds, seed=args.seed)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    manifest[keep + ["split"] + (["cv_fold"] if args.cv_folds else [])].to_csv(args.out, index=False)
    digest = file_sha256(args.out)
    with open(args.out.replace(".csv", "_report.json"), "w") as fh:
        json.dump({"seed": args.seed, "ratios": DEFAULT_RATIOS,
                   "sha256": digest, "summary": report}, fh, indent=2)

    print(f"\nmanifest -> {args.out}")
    print(f"sha256   -> {digest}")
    print("Freeze this hash in the report; any number without it is not reproducible.")


if __name__ == "__main__":
    main()
