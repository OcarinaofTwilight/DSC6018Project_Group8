"""Exercise kaggle_download.py against a local HTTP server (no Kaggle account needed).

    python tests/test_kaggle_download.py

The tool's only Kaggle-specific part is the URL prefix and the Bearer header, so serving
a fixture zip from 127.0.0.1 exercises the whole download path -- including --resume and
--unzip -- without touching the network or needing credentials.
"""
from __future__ import annotations

import functools
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools",
                    "kaggle_download.py")
FAIL = []


def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        FAIL.append(name)


def run(args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    e.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run([sys.executable, TOOL] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=e)


def serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def main():
    tmp_root = os.environ.get("KDL_TMP") or tempfile.gettempdir()
    tmp = os.path.join(tmp_root, "_kdl_test")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)

    # fixture: a zip shaped like the Kaggle image archives
    payload = os.path.join(tmp, "payload.zip")
    with zipfile.ZipFile(payload, "w") as zf:
        zf.writestr("train/ISIC_0001.jpg", b"x" * 200_000)
        zf.writestr("train/ISIC_0002.jpg", b"y" * 200_000)

    srv, base = serve(tmp)
    env = {"KAGGLE_API_TOKEN": "KGAT_test_only_not_real"}
    try:
        out_zip = os.path.join(tmp, "dl", "payload.zip")
        dest = os.path.join(tmp, "dl")
        r = run(["--api-path", f"{base}/payload.zip", "--out", out_zip,
                 "--unzip", "--dest", dest], env)
        check("download + unzip over http", r.returncode == 0,
              (r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout) else "")
        check("zip removed after extract", not os.path.exists(out_zip))
        check("two files extracted",
              os.path.exists(os.path.join(dest, "train", "ISIC_0001.jpg")) and
              os.path.exists(os.path.join(dest, "train", "ISIC_0002.jpg")))

        # --keep-zip
        keep = os.path.join(tmp, "keep", "p.zip")
        r = run(["--api-path", f"{base}/payload.zip", "--out", keep, "--unzip",
                 "--dest", os.path.join(tmp, "keep", "d"), "--keep-zip"], env)
        check("--keep-zip keeps the archive", r.returncode == 0 and os.path.exists(keep))

        # --resume on a half file
        part = os.path.join(tmp, "part.zip")
        with open(part, "wb") as fh:
            fh.write(open(payload, "rb").read()[:1000])
        r = run(["--api-path", f"{base}/payload.zip", "--out", part, "--resume"], env)
        same = open(part, "rb").read() == open(payload, "rb").read()
        check("--resume completes a partial file", r.returncode == 0 and same,
              f"size={os.path.getsize(part)}")

        # missing token -> clear message, non-zero exit
        r = run(["--api-path", f"{base}/payload.zip", "--out", os.path.join(tmp, "c.zip")],
                {"KAGGLE_API_TOKEN": ""})
        out = (r.stdout or "") + (r.stderr or "")
        check("missing token exits non-zero with a message", r.returncode != 0 and "令牌" in out)

        # 404 from the server (wrong slug)
        r = run(["--api-path", f"{base}/nope.zip", "--out", os.path.join(tmp, "n.zip")], env)
        out = (r.stdout or "") + (r.stderr or "")
        check("404 explains a wrong slug", r.returncode != 0 and "404" in out, out.strip()[:80])

        # url / header construction and the error-message table
        sys.path.insert(0, os.path.dirname(TOOL))
        import kaggle_download as K
        req = K.request("datasets/download/a/b", "TOK")
        check("api path joins the v1 base", req.full_url == f"{K.API}/datasets/download/a/b",
              req.full_url)
        check("absolute http url passes through",
              K.request(f"{base}/x.zip", "TOK").full_url == f"{base}/x.zip")
        check("bearer header set", req.get_header("Authorization") == "Bearer TOK")
        check("403 explains Accept Rules", "Accept Rules" in K.explain(403, "x"))
        check("404 suggests --list-datasets", "--list-datasets" in K.explain(404, "x"))
        check("human() formats sizes", K.human(1536) == "1.5 KB", K.human(1536))
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED: {FAIL}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
