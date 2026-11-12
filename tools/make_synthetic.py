"""Generate a synthetic ISIC-2020-shaped metadata table for dry runs.

Used only to exercise split.py / report.py / figures.py without the 30 GB dataset.
Shape and label balance match the real training partition (33,126 images, 2,056
patients, 584 melanomas) so that the printed summaries look like the real thing.

    python tools/make_synthetic.py --out data_synth/train.csv
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

SITES = ["torso", "lower extremity", "upper extremity", "head/neck",
         "palms/soles", "oral/genital"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data_synth/train.csv")
    ap.add_argument("--patients", type=int, default=2056)
    ap.add_argument("--images", type=int, default=33126)
    ap.add_argument("--positives", type=int, default=584)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)

    # heavy-tailed images per patient: most have 1-8 images, a few have hundreds
    w = rng.pareto(0.9, args.patients) + 1.0
    counts = np.floor(w / w.sum() * args.images).astype(int) + 1
    while counts.sum() > args.images:
        counts[rng.integers(0, args.patients)] -= 1
        counts = np.maximum(counts, 1)
    while counts.sum() < args.images:
        counts[rng.integers(0, args.patients)] += 1

    pid = np.repeat([f"IP_{i:07d}" for i in range(args.patients)], counts)
    n = pid.size

    patient_pos = rng.random(args.patients) < args.positives / args.patients
    pos = np.repeat(patient_pos, counts).astype(int)
    # force the exact positive count
    need = args.positives - int(pos.sum())
    if need > 0:
        flip = rng.choice(np.flatnonzero(pos == 0), size=need, replace=False)
        pos[flip] = 1
    elif need < 0:
        flip = rng.choice(np.flatnonzero(pos == 1), size=-need, replace=False)
        pos[flip] = 0

    age = rng.normal(55, 16, n).clip(5, 90).round()
    age[rng.random(n) < 0.06] = np.nan
    sex = rng.choice(["male", "female", None], size=n, p=[0.5, 0.42, 0.08])
    site = rng.choice(SITES + [None], size=n, p=[0.3, 0.2, 0.2, 0.15, 0.03, 0.02, 0.1])

    df = pd.DataFrame({
        "image_name": [f"ISIC_{i:07d}" for i in range(n)],
        "patient_id": pid,
        "lesion_id": [f"IL_{p.split('_')[1]}_{k % 3}" for k, p in enumerate(pid)],
        "target": pos,
        "benign_malignant": np.where(pos == 1, "malignant", "benign"),
        "age_approx": age,
        "sex": sex,
        "anatom_site_general_challenge": site,
    })
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"{len(df)} rows, {df.patient_id.nunique()} patients, "
          f"{int(df.target.sum())} melanomas ({df.target.mean():.4f}) -> {args.out}")


if __name__ == "__main__":
    main()
