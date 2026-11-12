"""Backbones and the image + clinical-metadata fusion head.

The proposal's contribution is not a new architecture, so this file is deliberately
boring: two standard ImageNet-pretrained backbones from timm, an optional small MLP
for (age, sex, anatomical site), and a concatenation head. That is the point -- the
claim is that the *evaluation protocol* changes the conclusion, so the model has to be
something a reader can reproduce in an afternoon.
"""
from __future__ import annotations

import torch
import torch.nn as nn

import hf_compat        # noqa: F401  must run BEFORE `import timm` (see its docstring)
import timm


class MetadataEncoder(nn.Module):
    """age (2 dims: scaled value + missing flag) | sex (3) | site (8) -> 64 dims."""

    def __init__(self, n_meta: int, hidden: int = 64, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_meta, hidden),
            nn.BatchNorm1d(hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )

    def forward(self, meta):
        return self.net(meta)


class MelanomaNet(nn.Module):
    def __init__(
        self,
        backbone: str = "efficientnet_b3",
        n_meta: int = 0,
        dropout: float = 0.3,
        drop_path: float = 0.1,
        pretrained: bool = True,
    ):
        super().__init__()
        self.backbone_name = backbone
        self.n_meta = n_meta
        # num_classes=0 -> pooled feature vector; keeps timm version differences out of
        # the rest of the code.
        self.encoder = timm.create_model(
            backbone, pretrained=pretrained, num_classes=0,
            drop_path_rate=drop_path, in_chans=3,
        )
        feat_dim = self.encoder.num_features

        if n_meta > 0:
            self.meta = MetadataEncoder(n_meta, hidden=64, dropout=dropout)
            head_in = feat_dim + 64
        else:
            self.meta = None
            head_in = feat_dim

        self.head = nn.Sequential(
            nn.BatchNorm1d(head_in),
            nn.Dropout(dropout),
            nn.Linear(head_in, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, 1),        # one logit: BCEWithLogitsLoss / focal operate here
        )

    def forward(self, img, meta=None):
        z = self.encoder(img)
        if self.meta is not None:
            if meta is None:
                raise ValueError("model was built with metadata but meta is None")
            z = torch.cat([z, self.meta(meta)], dim=1)
        return self.head(z).squeeze(1)


def check_pretrained_deps(backbone: str) -> None:
    """Turn timm's misleading ImportError into an actionable one.

    timm 1.0.x does `from huggingface_hub import repo_type_and_id_from_hf_id`, which
    huggingface_hub 2.x removed. timm catches the ImportError and later raises
    "Hugging Face hub model specified but package not installed" -- which is wrong: the
    package *is* installed, at an incompatible major version. This check says so before
    the confusing error appears.
    """
    try:
        import huggingface_hub as hf_hub
        from timm.models import _hub
    except Exception:                       # pragma: no cover - timm internals moved
        return
    if getattr(_hub, "_has_hf_hub", True):
        return
    raise RuntimeError(
        f"timm {timm.__version__} 与 huggingface_hub {hf_hub.__version__} 不兼容："
        "timm 需要的 repo_type_and_id_from_hf_id 在 huggingface_hub 2.x 已被移除。\n"
        '  修（跳过依赖解析，通常几秒完成）：\n'
        '    .venv\\Scripts\\python.exe -m pip install --no-deps --only-binary=:all: '
        '"huggingface_hub==0.25.2"\n'
        '  验证： .venv\\Scripts\\python.exe -c "import timm.models._hub as h; print(h._has_hf_hub)"'
        "   # 应为 True"
    )


def build_model(backbone: str, n_meta: int, pretrained: bool = True) -> MelanomaNet:
    if pretrained:
        check_pretrained_deps(backbone)
    # resnet50 has no drop_path in the same sense; timm tolerates the kwarg for both
    drop_path = 0.1 if "efficientnet" in backbone else 0.0
    return MelanomaNet(backbone=backbone, n_meta=n_meta, drop_path=drop_path,
                       pretrained=pretrained)


def count_params(model: nn.Module) -> str:
    total = sum(p.numel() for p in model.parameters())
    train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return f"{total/1e6:.1f}M total / {train/1e6:.1f}M trainable"
