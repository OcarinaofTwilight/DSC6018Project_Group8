"""Assemble the local-run guide (Windows + RTX 2060 Max-Q).

    python tools/build_local_guide.py --out ../6018_Local_Guide.docx
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import content_local
from docx_kit import Kit


def build(out_path: str):
    k = Kit("ISIC 2020 · 本机运行指南（RTX 2060 Max-Q）")
    content_local.cover(k)
    content_local.ch0(k)
    content_local.ch1(k)
    content_local.ch2(k)
    content_local.ch3(k)
    content_local.ch4(k)
    content_local.ch5(k)
    content_local.ch6(k)
    content_local.ch7(k)
    content_local.ch8(k)
    content_local.ch9(k)
    content_local.appendix(k)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    k.doc.save(out_path)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="6018_Local_Guide.docx")
    args = ap.parse_args()
    print("saved", build(args.out))
