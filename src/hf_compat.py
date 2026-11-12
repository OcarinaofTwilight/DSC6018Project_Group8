"""Compatibility shim: make timm 1.0.x work with huggingface_hub 2.x.

timm 1.0.x does, at import time::

    from huggingface_hub import (create_repo, get_hf_file_metadata, hf_hub_download,
                                 hf_hub_url, repo_type_and_id_from_hf_id, upload_folder)

`repo_type_and_id_from_hf_id` was **removed** in huggingface_hub 2.0. The ImportError is
caught inside timm, which then reports

    RuntimeError: Hugging Face hub model specified but package not installed

which is misleading: the package *is* installed, the symbol is gone. Every other symbol
timm needs still exists in 2.x, and `hf_hub_download` still accepts `library_name` /
`library_version`, so restoring that one helper is enough.

Importing this module patches the attribute **only when it is missing**, so it is a no-op
on huggingface_hub 0.2x/1.x. Import it before `timm` (see `models.py`).
"""
from __future__ import annotations

_PREFIXES = (("models/", "model"), ("datasets/", "dataset"), ("spaces/", "space"))


def repo_type_and_id_from_hf_id(hf_id: str, endpoint=None):
    """Same contract as the pre-2.0 helper: (repo_type, repo_id, revision).

    repo_type is None for a plain "owner/name" model id, which is what timm passes.
    """
    hf_id = str(hf_id)
    root = f"{endpoint.rstrip('/')}/" if endpoint else None
    if root and hf_id.startswith(root):
        hf_id = hf_id[len(root):]

    repo_type = None
    for prefix, kind in _PREFIXES:
        if hf_id.startswith(prefix):
            repo_type, hf_id = kind, hf_id[len(prefix):]
            break

    if "@" in hf_id:
        hf_id, revision = hf_id.rsplit("@", 1)
    else:
        revision = None
    return repo_type, hf_id, revision


def patch() -> bool:
    """Return True if the shim was installed, False if the real helper was there."""
    try:
        import huggingface_hub as hh
    except ImportError:                     # timm will raise its own, accurate error
        return False
    if hasattr(hh, "repo_type_and_id_from_hf_id"):
        return False
    hh.repo_type_and_id_from_hf_id = repo_type_and_id_from_hf_id   # type: ignore[attr-defined]
    return True


PATCHED = patch()
