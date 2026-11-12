"""Inference, temperature scaling and the test-set evaluation entry point."""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd
import torch

from data import ISICDataset, TTA_FOLDS, make_loader, MetaEncoder
from metrics import apply_temperature as apply_temperature_np
from metrics import summary, temperature_nll
from models import build_model


def predict(model, loader, device, with_meta: bool):
    """Return (probs, targets, row_indices) for one pass over `loader`."""
    model.eval()
    probs, ys, idxs = [], [], []
    with torch.no_grad():
        for batch in loader:
            img = batch["image"].to(device, non_blocking=True)
            meta = batch["meta"].to(device, non_blocking=True) if with_meta else None
            with torch.autocast(device_type=device.type, dtype=torch.float16,
                                enabled=device.type == "cuda"):
                logit = model(img, meta)
            probs.append(torch.sigmoid(logit.float()).cpu().numpy())
            ys.append(batch["target"].numpy())
            idxs.append(batch["index"].numpy())
    return np.concatenate(probs), np.concatenate(ys), np.concatenate(idxs)


def infer_split(model, df, img_dir, size, device, meta_encoder=None, ext=".jpg",
                batch_size=64, workers=2, tta=True):
    """Average probabilities over the 4 flip variants (cheap, order-preserving TTA)."""
    n = len(df)
    acc = np.zeros(n, dtype=np.float64)
    folds = TTA_FOLDS if tta else [(False, False)]
    for flip_h, flip_v in folds:
        ds = ISICDataset(df, img_dir, size=size, train=False,
                         meta_encoder=meta_encoder, ext=ext, tta=(flip_h, flip_v))
        loader = make_loader(ds, batch_size, shuffle=False, workers=workers)
        p, y, idx = predict(model, loader, device, with_meta=meta_encoder is not None)
        acc[idx] += p
    out = df.reset_index(drop=True).copy()
    out["prob"] = acc / len(folds)
    return out


def fit_temperature(df_val) -> float:
    """One scalar T minimising NLL on the validation split (never on test)."""
    p = np.clip(df_val["prob"].to_numpy(), 1e-6, 1 - 1e-6)
    return temperature_nll(df_val["target"].to_numpy(), np.log(p / (1 - p)))


def apply_temperature(df, T: float):
    """Apply a temperature to a prediction frame; keeps every other column intact."""
    out = df.copy()
    out["prob"] = apply_temperature_np(df["prob"].to_numpy(), T)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--img-dir", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="test", choices=["val", "test"])
    ap.add_argument("--img-size", type=int, default=256)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--ext", default=".jpg")
    ap.add_argument("--no-tta", action="store_true")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    state = torch.load(args.ckpt, map_location=device, weights_only=False)
    cfg = state["cfg"]
    meta_encoder = None
    if cfg.get("meta"):
        meta_encoder = MetaEncoder.from_json(os.path.join(os.path.dirname(args.ckpt), "meta_encoder.json"))

    model = build_model(cfg["model"], meta_encoder.dim if meta_encoder else 0, pretrained=False)
    model.load_state_dict(state["model"])
    model.to(device)

    man = pd.read_csv(args.manifest)
    df = man[man["split"] == args.split]
    pred = infer_split(model, df, args.img_dir, args.img_size, device,
                       meta_encoder=meta_encoder, ext=args.ext,
                       batch_size=args.batch_size, workers=args.workers,
                       tta=not args.no_tta)

    res = summary(pred["target"].to_numpy(), pred["prob"].to_numpy(),
                  spec=0.80, with_slope=True)
    print(json.dumps(res, indent=2))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    pred[["image_name", "patient_id", "target", "prob"]].to_csv(args.out, index=False)
    with open(args.out.replace(".csv", "_metrics.json"), "w") as fh:
        json.dump({"cfg": cfg, "metrics": res}, fh, indent=2)
    print(f"predictions -> {args.out}")


if __name__ == "__main__":
    main()
