"""Training entry point -- one experiment = one command = one directory.

Designed for a Colab-style environment that can die at any moment:

* every epoch overwrites `last.pt` and appends a row to `log.csv`, both inside the
  run directory (point `--out-dir` at Google Drive and a disconnect costs you at most
  one epoch);
* `--resume` continues from `last.pt` without touching the schedule;
* `--limit-batches` runs a 2-minute smoke test of the whole pipeline before you spend
  GPU hours on it.

    python src/train.py --manifest manifests/split_seed42.csv \
        --img-dir /content/data/jpeg-melanoma-256x256/train \
        --model efficientnet_b3 --loss bce --epochs 12 \
        --out-dir /content/drive/MyDrive/runs/b3_bce
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import json
import math
import os
import random
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from data import ISICDataset, MetaEncoder, make_loader, make_weighted_sampler
from evaluate import predict
from losses import build_loss, describe_losses
from metrics import auprc, auroc, sens_at_spec
from models import build_model, count_params


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = True       # T4: benchmark beats determinism


def amp_context(enabled: bool):
    if not enabled:
        return contextlib.nullcontext()
    try:
        return torch.amp.autocast("cuda", dtype=torch.float16)
    except (AttributeError, TypeError):
        return torch.cuda.amp.autocast(dtype=torch.float16)


def make_scaler(enabled: bool):
    try:
        return torch.amp.GradScaler("cuda", enabled=enabled)
    except (AttributeError, TypeError):
        return torch.cuda.amp.GradScaler(enabled=enabled)


def lr_at(step: int, total: int, base_lr: float, warmup_frac: float = 0.05) -> float:
    warm = max(1, int(total * warmup_frac))
    if step < warm:
        return base_lr * (step + 1) / warm
    prog = (step - warm) / max(1, total - warm)
    return base_lr * 0.5 * (1.0 + math.cos(math.pi * prog))


def evaluate_split(model, df, img_dir, size, device, meta_encoder, batch_size,
                   workers, ext, max_batches=None):
    ds = ISICDataset(df, img_dir, size=size, train=False, meta_encoder=meta_encoder, ext=ext)
    loader = make_loader(ds, batch_size, shuffle=False, workers=workers)
    model.eval()
    probs, ys = [], []
    with torch.no_grad():
        for i, batch in enumerate(loader):
            if max_batches and i >= max_batches:
                break
            img = batch["image"].to(device, non_blocking=True)
            meta = batch["meta"].to(device, non_blocking=True) if meta_encoder else None
            with amp_context(device.type == "cuda"):
                logit = model(img, meta)
            probs.append(torch.sigmoid(logit.float()).cpu().numpy())
            ys.append(batch["target"].numpy())
    p = np.concatenate(probs)
    y = np.concatenate(ys).astype(int)
    sens, spec, _ = sens_at_spec(y, p, spec=0.80)
    return {"val_auroc": auroc(y, p), "val_auprc": auprc(y, p),
            "val_sens80": sens, "val_spec": spec}, p, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--img-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model", default="efficientnet_b3")
    ap.add_argument("--loss", default="bce")
    ap.add_argument("--meta", action="store_true", help="concatenate clinical metadata")
    ap.add_argument("--img-size", type=int, default=256)
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dropout", type=float, default=0.3)
    ap.add_argument("--sampler-power", type=float, default=0.0,
                    help="0 = off; 0.5 = mild oversampling; 1.0 = full inverse-frequency")
    ap.add_argument("--select-metric", default="val_auprc")
    ap.add_argument("--ext", default=".jpg")
    ap.add_argument("--limit-batches", type=int, default=0, help="smoke test only")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--no-amp", action="store_true")
    ap.add_argument("--no-pretrained", action="store_true",
                    help="skip ImageNet weights: pipeline debugging only, metrics are not usable")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = (not args.no_amp) and device.type == "cuda"

    man = pd.read_csv(args.manifest)
    tr_df = man[man["split"] == "train"].reset_index(drop=True)
    va_df = man[man["split"] == "val"].reset_index(drop=True)

    meta_encoder = None
    if args.meta:
        meta_encoder = MetaEncoder().fit(tr_df)
        meta_encoder.to_json(os.path.join(args.out_dir, "meta_encoder.json"))

    n_pos = int(tr_df["target"].sum())
    n_neg = int(len(tr_df) - n_pos)
    print(describe_losses(n_pos, n_neg))
    criterion = build_loss(args.loss, n_pos, n_neg).to(device)

    try:
        model = build_model(args.model, meta_encoder.dim if meta_encoder else 0,
                            pretrained=not args.no_pretrained).to(device)
    except Exception as exc:
        low = f"{type(exc).__name__} {exc}".lower()
        print(f"\n[!] 构建模型失败：{type(exc).__name__}: {str(exc)[:300]}")
        if "huggingface_hub" in low or "package not installed" in low:
            print("    timm 1.x 从 Hugging Face hub 取权重，但 venv 里没装 huggingface_hub。")
            print("    修：.venv\\Scripts\\python.exe -m pip install huggingface_hub")
        elif any(k in low for k in ("huggingface", "connection", "urlopen", "ssl",
                                    "timed out", "timeout", "certificate", "download", "offline")):
            print("    看起来是预训练权重下载失败（timm 1.x 默认从 huggingface.co 取）。")
            print("    ① 设 HF_ENDPOINT=https://hf-mirror.com 再试（scripts\\train.ps1 -HfMirror）")
            print("    ② 或先加 --no-pretrained 只验证管线（指标不可用，不能写报告）")
        elif "out of memory" in low:
            print("    显存不足：把 --batch-size 降到 12 或 8，--workers 降到 2")
        elif "unknown model" in low or "does not exist" in low:
            print("    模型名不被当前 timm 认可：pip show timm，确认是 1.0.9")
        print("    不带预训练权重的快速验证：scripts\\train.ps1 -Smoke -NoPretrained\n")
        raise
    print(f"{args.model}: {count_params(model)}"
          + ("  [random init: --no-pretrained]" if args.no_pretrained else ""))

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    train_ds = ISICDataset(tr_df, args.img_dir, size=args.img_size, train=True,
                           meta_encoder=meta_encoder, ext=args.ext)
    sampler = make_weighted_sampler(tr_df, args.sampler_power) if args.sampler_power > 0 else None
    train_loader = make_loader(train_ds, args.batch_size, shuffle=True,
                               workers=args.workers, sampler=sampler)

    steps_per_epoch = len(train_loader)
    total_steps = steps_per_epoch * args.epochs
    if args.limit_batches:
        total_steps = min(total_steps, args.limit_batches * args.epochs)

    start_epoch, global_step, best = 0, 0, -np.inf
    ckpt_last = os.path.join(args.out_dir, "last.pt")
    if args.resume and os.path.exists(ckpt_last):
        state = torch.load(ckpt_last, map_location=device, weights_only=False)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        start_epoch = state["epoch"] + 1
        global_step = state["global_step"]
        best = state.get("best", -np.inf)
        print(f"resumed at epoch {start_epoch}, best {args.select_metric}={best:.4f}")

    cfg = vars(args).copy()
    scaler = make_scaler(use_amp)

    log_path = os.path.join(args.out_dir, "log.csv")
    new_log = not os.path.exists(log_path)
    log_fh = open(log_path, "a", newline="")
    log = csv.writer(log_fh)
    if new_log:
        log.writerow(["epoch", "lr", "train_loss", "val_auroc", "val_auprc",
                      "val_sens80", "seconds", "best"])

    for epoch in range(start_epoch, args.epochs):
        t0 = time.time()
        model.train()
        run_loss, seen = 0.0, 0
        for i, batch in enumerate(train_loader):
            if args.limit_batches and i >= args.limit_batches:
                break
            lr = lr_at(global_step, total_steps, args.lr)
            for g in optimizer.param_groups:
                g["lr"] = lr
            img = batch["image"].to(device, non_blocking=True)
            meta = batch["meta"].to(device, non_blocking=True) if meta_encoder else None
            y = batch["target"].to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with amp_context(use_amp):
                logit = model(img, meta)
                loss = criterion(logit, y)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()

            run_loss += loss.item() * y.numel()
            seen += y.numel()
            global_step += 1

        metrics, _, _ = evaluate_split(
            model, va_df, args.img_dir, args.img_size, device, meta_encoder,
            args.batch_size, args.workers, args.ext, max_batches=args.limit_batches or None)
        score = metrics[args.select_metric]
        improved = score > best
        if improved:
            best = score

        torch.save({"model": model.state_dict(), "cfg": cfg, "epoch": epoch,
                    "global_step": global_step, "best": best,
                    "metrics": metrics}, ckpt_last)
        if improved:
            torch.save({"model": model.state_dict(), "cfg": cfg, "epoch": epoch,
                        "metrics": metrics}, os.path.join(args.out_dir, "best.pt"))

        log.writerow([epoch, f"{lr:.3e}", f"{run_loss / max(seen, 1):.5f}",
                      f"{metrics['val_auroc']:.5f}", f"{metrics['val_auprc']:.5f}",
                      f"{metrics['val_sens80']:.4f}", f"{time.time() - t0:.0f}",
                      int(improved)])
        log_fh.flush()
        print(f"epoch {epoch:02d} loss {run_loss / max(seen, 1):.4f} "
              f"auroc {metrics['val_auroc']:.4f} auprc {metrics['val_auprc']:.4f} "
              f"sens80 {metrics['val_sens80']:.3f} {'*' if improved else ''} "
              f"({time.time() - t0:.0f}s)", flush=True)

    log_fh.close()
    with open(os.path.join(args.out_dir, "cfg.json"), "w") as fh:
        json.dump(cfg, fh, indent=2)
    print(f"done. best {args.select_metric} = {best:.4f}")


if __name__ == "__main__":
    main()
