"""Assemble the v2 tutorial.

    python tools/build_tutorial_v2.py --out ../6018_Tutorial_Implementation.docx
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import content_a
import content_b
from docx_kit import Kit


def build(out_path: str):
    k = Kit("ISIC 2020 黑色素瘤检测与校准 · 实现教程 v2.0")
    content_a.cover(k)
    content_a.toc(k)
    content_a.ch0(k)
    content_a.ch1(k)
    content_a.ch2(k)
    content_a.ch3(k)
    content_a.ch4(k)
    content_a.ch5(k)
    content_a.ch6(k)
    content_b.ch7(k)
    content_b.ch8(k)
    content_b.ch9(k)
    content_b.ch10(k)
    content_b.ch11(k)
    content_b.ch12(k)
    content_b.ch13(k)
    content_b.appendix(k)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    k.doc.save(out_path)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="6018_Tutorial_Implementation.docx")
    args = ap.parse_args()
    print("saved", build(args.out))
