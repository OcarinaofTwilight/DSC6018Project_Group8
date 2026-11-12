"""Day-1 data health check -- run this before you trust anything downstream.

    python tools/inspect_data.py --csv data/train.csv --img-dir data/jpeg-melanoma-256x256/train

It answers the eight questions that decide whether the rest of the project is
meaningful, and it fails loudly instead of silently: wrong label column, missing
patient ids, duplicated image rows, missing image files, and label-shaped columns that
must never enter the metadata branch.

Exit code is 0 only when no blocking problem was found.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

REQUIRED = ["image_name", "patient_id", "target"]

# Columns that encode the label or that a real triage setting does not have. Presence is
# fine (the challenge ships them), *use* is not -- data.py only reads three fields.
FORBIDDEN = ["diagnosis", "benign_malignant", "melanoma", "nevus", "seborrheic_keratosis"]
FORBIDDEN_PREFIX = ("tbp_lv_", "tbp_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/train.csv")
    ap.add_argument("--img-dir", default=None, help="optional: verify image files exist")
    ap.add_argument("--ext", default=".jpg")
    ap.add_argument("--sample", type=int, default=200, help="how many files to stat")
    args = ap.parse_args()

    problems, warnings = [], []
    df = pd.read_csv(args.csv)
    print(f"file      : {args.csv}")
    print(f"shape     : {df.shape[0]} rows x {df.shape[1]} columns")

    for c in REQUIRED:
        if c not in df.columns:
            problems.append(f"missing required column {c!r}")
    if problems:
        print("\n".join(f"[FAIL] {p}" for p in problems))
        sys.exit(1)

    y = pd.to_numeric(df["target"], errors="coerce")
    if y.isna().any():
        problems.append(f"{int(y.isna().sum())} rows have a non-numeric target")
    print(f"label     : {int(np.nansum(y))} positive / {len(df)} "
          f"-> prevalence {np.nanmean(y):.4f} (1:{1 / max(np.nanmean(y), 1e-9):.1f})")

    n_pat = df["patient_id"].nunique(dropna=True)
    print(f"patients  : {n_pat}  ({len(df) / max(n_pat, 1):.1f} images/patient on average)")
    if df["patient_id"].isna().any():
        warnings.append(f"{int(df['patient_id'].isna().sum())} rows without patient_id "
                        "(split.py gives each its own pseudo-patient)")
    per = df.groupby("patient_id").size()
    if len(per):
        q = np.percentile(per, [50, 90, 99, 100]).astype(int)
        print(f"images/pt : median {q[0]}  p90 {q[1]}  p99 {q[2]}  max {q[3]}")

    if "lesion_id" in df.columns:
        per_les = df.groupby("lesion_id")["patient_id"].nunique()
        if (per_les > 1).any():
            problems.append(f"{int((per_les > 1).sum())} lesion_id values span >1 patient")
        print(f"lesions   : {df['lesion_id'].nunique()}")

    dup = int(df["image_name"].duplicated().sum())
    print(f"duplicates: {dup} duplicated image_name values")
    if dup:
        problems.append("duplicated image_name rows would double-count in a bootstrap")

    for c in ["age_approx", "sex", "anatom_site_general_challenge"]:
        if c in df.columns:
            miss = float(pd.isna(df[c]).mean())
            print(f"missing   : {c:32s} {100 * miss:5.1f}%")
        else:
            warnings.append(f"{c} absent -> the metadata branch cannot be built")

    present = [c for c in df.columns if c in FORBIDDEN
               or c.startswith(FORBIDDEN_PREFIX)]
    if present:
        print(f"label-shaped columns present (use NONE of them): {len(present)}")
        print("            " + ", ".join(present[:8]) + (" ..." if len(present) > 8 else ""))
        warnings.append("data.py must keep ignoring " + ", ".join(present[:3]) + " ...")

    if args.img_dir:
        files = glob.glob(os.path.join(args.img_dir, "**", f"*{args.ext}"), recursive=True)
        print(f"images    : {len(files)} files under {args.img_dir} (*{args.ext})")
        if not files:
            problems.append(f"no *{args.ext} files found under {args.img_dir}")
        else:
            sample = df["image_name"].head(args.sample)
            missing = [n for n in sample
                       if not os.path.exists(os.path.join(args.img_dir, f"{n}{args.ext}"))]
            print(f"probe     : {args.sample - len(missing)}/{len(sample)} of the first "
                  f"{args.sample} names resolve to a file")
            if missing:
                problems.append(f"{len(missing)} of the first {len(sample)} image names have "
                                f"no file, e.g. {missing[0]}{args.ext}")

    print()
    for w in warnings:
        print(f"[warn] {w}")
    for p in problems:
        print(f"[FAIL] {p}")
    if problems:
        sys.exit(1)
    print("[ok] no blocking problem found")


if __name__ == "__main__":
    main()
