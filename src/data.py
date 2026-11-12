"""Dataset, augmentation and clinical-metadata encoding for ISIC 2020.

Two rules encoded here, because they are the two easiest ways to leak or to lie:

1. The metadata encoder (median age, category vocabulary) is fit on the TRAIN split
   only and saved to JSON, so the val/test statistics never touch the encoder.
2. Only age, sex and anatomical site are used. The challenge CSV also ships
   `diagnosis`, the one-hot `melanoma`/`nevus`/`seborrheic keratosis` columns and the
   `tbp_lv_*` total-body-photography features; those are label-derived or unavailable
   in a real triage setting, and including them turns the experiment into a
   leakage demo. `data.py` refuses to build a metadata vector from them.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

SEX_CATEGORIES = ("male", "female", "unknown")
SITE_CATEGORIES = (
    "torso", "lower extremity", "upper extremity", "head/neck",
    "palms/soles", "oral/genital", "unknown",
)


# --------------------------------------------------------------------------- metadata
class MetaEncoder:
    """Deterministic 13-dim clinical vector: [age, age_missing, sex(3), site(7)]."""

    def __init__(self, age_median: float = 50.0):
        self.age_median = float(age_median)

    @property
    def dim(self) -> int:
        return 2 + len(SEX_CATEGORIES) + len(SITE_CATEGORIES)

    def fit(self, df: pd.DataFrame) -> "MetaEncoder":
        if "age_approx" in df.columns:
            self.age_median = float(pd.to_numeric(df["age_approx"], errors="coerce").median())
        return self

    def transform(self, row) -> np.ndarray:
        age = row.get("age_approx", np.nan)
        try:
            age = float(age)
        except (TypeError, ValueError):
            age = np.nan
        age_missing = float(np.isnan(age))
        age = self.age_median if np.isnan(age) else age

        sex = str(row.get("sex", "") or "").strip().lower()
        sex = sex if sex in ("male", "female") else "unknown"

        site = str(row.get("anatom_site_general_challenge", "") or "").strip().lower()
        site = site if site in SITE_CATEGORIES[:-1] else "unknown"

        v = [age / 100.0, age_missing]
        v += [1.0 if sex == c else 0.0 for c in SEX_CATEGORIES]
        v += [1.0 if site == c else 0.0 for c in SITE_CATEGORIES]
        return np.asarray(v, dtype=np.float32)

    def to_json(self, path: str):
        with open(path, "w") as fh:
            json.dump({"age_median": self.age_median,
                       "sex": SEX_CATEGORIES, "site": SITE_CATEGORIES}, fh, indent=2)

    @classmethod
    def from_json(cls, path: str) -> "MetaEncoder":
        with open(path) as fh:
            d = json.load(fh)
        return cls(age_median=d["age_median"])


# --------------------------------------------------------------------------- transforms
def build_transforms(size: int, train: bool):
    if train:
        return transforms.Compose([
            transforms.RandomResizedCrop(size, scale=(0.75, 1.0), ratio=(0.85, 1.18)),
            transforms.RandomHorizontalFlip(0.5),
            transforms.RandomVerticalFlip(0.5),          # dermoscopy has no canonical up
            transforms.RandomRotation(20),
            transforms.ColorJitter(0.15, 0.15, 0.10, 0.03),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])
    return transforms.Compose([
        transforms.Resize(int(round(size * 1.14))),      # resize + crop, not squash
        transforms.CenterCrop(size),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


TTA_FOLDS = [(False, False), (True, False), (False, True), (True, True)]


# --------------------------------------------------------------------------- dataset
class ISICDataset(Dataset):
    def __init__(self, df: pd.DataFrame, img_dir: str, size: int = 256,
                 train: bool = False, meta_encoder: MetaEncoder | None = None,
                 ext: str = ".jpg", tta: tuple = (False, False)):
        self.df = df.reset_index(drop=True)
        self.img_dir = img_dir
        self.ext = ext
        self.meta_encoder = meta_encoder
        self.tf = build_transforms(size, train)
        self.tta = tta
        missing = [n for n in self.df["image_name"].head(200)
                   if not os.path.exists(os.path.join(img_dir, f"{n}{ext}"))]
        if missing:
            raise FileNotFoundError(
                f"{len(missing)} images missing under {img_dir}, e.g. {missing[0]}{ext}. "
                "Check --img-dir and --ext."
            )

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        row = self.df.iloc[i]
        path = os.path.join(self.img_dir, f"{row['image_name']}{self.ext}")
        img = Image.open(path).convert("RGB")
        img = self.tf(img)
        if self.tta[0]:
            img = torch.flip(img, dims=[2])
        if self.tta[1]:
            img = torch.flip(img, dims=[1])
        out = {
            "image": img,
            "target": torch.tensor(float(row["target"]), dtype=torch.float32),
            "index": i,
        }
        if self.meta_encoder is not None:
            out["meta"] = torch.from_numpy(self.meta_encoder.transform(row))
        return out


def make_loader(ds: ISICDataset, batch_size: int, shuffle: bool, workers: int = 2,
                sampler=None) -> DataLoader:
    return DataLoader(
        ds, batch_size=batch_size, shuffle=shuffle if sampler is None else False,
        sampler=sampler, num_workers=workers, pin_memory=True,
        drop_last=shuffle, persistent_workers=workers > 0,
    )


def make_weighted_sampler(df: pd.DataFrame, power: float = 1.0):
    """Optional: inverse-frequency sampling. `power`<1 softens it (power=0.5 is a mild
    oversampling that usually keeps calibration better than full 1.0)."""
    counts = df["target"].value_counts().to_dict()
    w = df["target"].map(lambda t: (1.0 / counts[t]) ** power).to_numpy()
    return WeightedRandomSampler(torch.as_tensor(w, dtype=torch.double),
                                 num_samples=len(df), replacement=True)
