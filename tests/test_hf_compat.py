"""Offline checks for the huggingface_hub compatibility shim.

    python tests/test_hf_compat.py

No network, no torch: it only exercises the id parser and checks that importing
`hf_compat` before timm makes timm's `_has_hf_hub` True on both hf_hub 0.2x and 2.x.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import hf_compat   # noqa: E402

FAIL = []


def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        FAIL.append(name)


def main():
    parse = hf_compat.repo_type_and_id_from_hf_id
    check("plain model id", parse("timm/efficientnet_b3.ra2_in1k")
          == (None, "timm/efficientnet_b3.ra2_in1k", None))
    check("models/ prefix", parse("models/owner/name") == ("model", "owner/name", None))
    check("datasets/ prefix", parse("datasets/owner/name") == ("dataset", "owner/name", None))
    check("revision suffix", parse("owner/name@v2") == (None, "owner/name", "v2"))
    check("endpoint prefix is stripped",
          parse("https://hf-mirror.com/owner/name", "https://hf-mirror.com")
          == (None, "owner/name", None))

    try:
        from timm.models import _hub
        check("timm sees the HF hub (its import block succeeded)", bool(_hub._has_hf_hub),
              f"patched={hf_compat.PATCHED}")
    except ImportError:
        print("[SKIP] timm not installed in this interpreter")

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED: {FAIL}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
