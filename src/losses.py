"""The three training conditions of the proposal, plus the weight schemes that matter.

All losses are binary-with-logits so that the same training loop, the same AMP
context and the same checkpoint format work for every condition. Nothing here changes
the model or the data pipeline -- the experiment isolates the objective.

Reference points
----------------
* plain BCE              : the null condition, calibrated by construction if the model
                           is well specified and trained long enough.
* inverse-prevalence BCE : pos_weight = n_neg / n_pos (about 55.7 on ISIC 2020).
                           This is the most aggressive reweighting and, as expected,
                           is the condition most likely to destroy calibration.
                           A milder alternative is the effective-number weight below.
* focal loss             : (1 - p_t)^gamma down-weights easy examples; because ~98 %
                           of the data is easy negatives this *focuses* the model on
                           hard cases, which usually raises AUPRC and flattens the
                           probability scale in an uncontrolled way.
"""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class SigmoidFocalLoss(nn.Module):
    """Binary focal loss on logits: -alpha_t (1 - p_t)^gamma log p_t."""

    def __init__(self, gamma: float = 2.0, alpha: float = 0.75, reduction: str = "mean"):
        super().__init__()
        self.gamma = gamma
        self.alpha = alpha
        self.reduction = reduction

    def forward(self, logits, targets):
        targets = targets.float()
        p = torch.sigmoid(logits)
        ce = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        p_t = p * targets + (1 - p) * (1 - targets)
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
        loss = alpha_t * (1 - p_t).pow(self.gamma) * ce
        return loss.mean() if self.reduction == "mean" else loss.sum()


def effective_number_weights(counts, beta: float = 0.9999):
    """Cui et al. (2019) class-balanced weights: (1-beta)/(1-beta^n), normalised to sum 2."""
    w = [(1.0 - beta) / (1.0 - beta ** max(n, 1)) for n in counts]
    s = sum(w)
    return [x * len(w) / s for x in w]


def build_loss(name: str, n_pos: int, n_neg: int, beta: float = 0.9999,
               gamma: float = 2.0, alpha: float = 0.75) -> nn.Module:
    name = name.lower()
    if name in ("bce", "ce", "plain"):
        return nn.BCEWithLogitsLoss()

    if name in ("wbce", "balanced", "invprev"):
        pos_weight = torch.tensor([n_neg / max(n_pos, 1)], dtype=torch.float32)
        return nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    if name in ("cb", "effective", "effective_number"):
        w = effective_number_weights([n_neg, n_pos], beta=beta)  # [w_neg, w_pos]
        weight = torch.tensor([w[1] / w[0]], dtype=torch.float32)  # relative pos weight
        return nn.BCEWithLogitsLoss(pos_weight=weight)

    if name == "focal":
        return SigmoidFocalLoss(gamma=gamma, alpha=alpha)

    raise ValueError(f"unknown loss {name!r}")


def describe_losses(n_pos: int, n_neg: int, beta: float = 0.9999) -> str:
    """Print the effective positive weight of each condition -- put this in the report."""
    eff = effective_number_weights([n_neg, n_pos], beta=beta)
    lines = [
        f"n_pos={n_pos}  n_neg={n_neg}  pos:neg = 1:{n_neg / max(n_pos, 1):.1f}",
        f"  bce     : pos_weight = 1.0",
        f"  wbce    : pos_weight = {n_neg / max(n_pos, 1):.2f}   (inverse prevalence)",
        f"  cb      : pos_weight = {eff[1] / eff[0]:.2f}   (beta={beta}, effective number)",
        f"  focal   : alpha=0.75 gamma=2.0  -> implicit pos weight 3.0 vs 1.0 on easy examples",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe_losses(n_pos=584, n_neg=32542))
    logits = torch.randn(64, requires_grad=True)
    y = (torch.rand(64) < 0.05).float()
    for cond in ("bce", "wbce", "cb", "focal"):
        loss = build_loss(cond, int(y.sum()), int((1 - y).sum()))(logits, y)
        print(f"{cond:6s} -> {loss.item():.4f}")
