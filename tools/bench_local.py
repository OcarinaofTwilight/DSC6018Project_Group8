"""Measure what THIS machine can actually do: peak VRAM and images/second.

    python tools/bench_local.py --batch-size 16 --img-size 256

It never downloads pretrained weights (pretrained=False) and never touches the dataset,
so it runs in ~30 s and answers the only two questions that matter before a long run:
  * does batch X @ size Y fit in 6 GB?
  * how many images/second, i.e. how long is one epoch of 23,188 images?

Also tries a few batch sizes when the first one OOMs, so the printed table tells you
what to pass as --batch-size.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from models import build_model, count_params   # noqa: E402

TRAIN_IMAGES = 23188      # the 70% split of the 33,126 public training images


def bench(model_name: str, batch: int, size: int, steps: int = 5, n_meta: int = 0):
    device = torch.device("cuda")
    model = build_model(model_name, n_meta, pretrained=False).to(device)
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    crit = torch.nn.BCEWithLogitsLoss()
    scaler = torch.amp.GradScaler("cuda")

    x = torch.randn(batch, 3, size, size, device=device)
    meta = torch.randn(batch, n_meta, device=device) if n_meta else None
    y = (torch.rand(batch, device=device) < 0.02).float()

    def one_step():
        opt.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", dtype=torch.float16):
            loss = crit(model(x, meta), y)
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()

    for _ in range(2):                       # warm up (cudnn autotune)
        one_step()
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(steps):
        one_step()
    torch.cuda.synchronize()
    dt = (time.time() - t0) / steps
    peak = torch.cuda.max_memory_allocated() / 1024 ** 3
    ips = batch / dt
    return ips, peak, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="efficientnet_b3")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--img-size", type=int, default=256)
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--meta", action="store_true")
    ap.add_argument("--sweep", action="store_true", help="try 32/24/16/12/8 and report")
    args = ap.parse_args()

    if not torch.cuda.is_available():
        sys.exit("CUDA 不可用：装成了 CPU 版 torch？见 scripts/setup.ps1")

    props = torch.cuda.get_device_properties(0)
    print(f"gpu      : {props.name}  {props.total_memory / 1024 ** 3:.1f} GB  sm_{props.major}{props.minor}")
    print(f"torch    : {torch.__version__}  cuda {torch.version.cuda}")
    print(f"settings : {args.model} @ {args.img_size}px, amp=fp16, meta={args.meta}")
    print()

    batches = [32, 24, 16, 12, 8] if args.sweep else [args.batch_size]
    for b in batches:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        try:
            ips, peak, model = bench(args.model, b, args.img_size, args.steps,
                                     n_meta=13 if args.meta else 0)
        except torch.cuda.OutOfMemoryError:
            print(f"batch {b:3d} : OOM")
            torch.cuda.empty_cache()
            continue
        epoch_min = TRAIN_IMAGES / ips / 60
        print(f"batch {b:3d} : {ips:6.1f} img/s   peak {peak:5.2f} GB   "
              f"epoch(23,188) {epoch_min:5.1f} min   12 epochs {12 * epoch_min:5.1f} min")
        del model
        torch.cuda.empty_cache()

    print()
    print(f"params   : {count_params(build_model(args.model, 13 if args.meta else 0, pretrained=False))}")
    print("把上面「batch .. <- 没有 OOM 的最大值」写进 scripts\\_common.ps1 的默认 --batch-size。")


if __name__ == "__main__":
    main()
