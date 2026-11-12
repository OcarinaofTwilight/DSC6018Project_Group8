"""Download from the Kaggle API with a Bearer token -- no `kaggle` package needed.

Why this exists: the `kaggle` CLI (1.7.x) writes credentials to `~/.kaggle` at *import*
time, so on a machine where that directory cannot be created it dies before it can even
read your token:

    PermissionError: [WinError 5] 拒绝访问。: 'C:\\Users\\<you>\\.kaggle'

It also predates the new `KGAT_...` API tokens. This script talks to the same REST API
with a plain `urllib` request, which means:

  * no `kaggle` package, no version constraints, no `~/.kaggle`;
  * it works with the new `KGAT_` tokens (`Authorization: Bearer ...`);
  * the token can live anywhere, e.g. `S:\\CityUStudy\\DSC6018_Project\\secrets\\access_token`;
  * a 30 GB download can be resumed with `--resume`.

Examples
--------
    # competition file (train.csv)
    python tools/kaggle_download.py \
        --api-path competitions/data/download/siim-isic-melanoma-classification/train.csv \
        --out data/train.csv.zip --unzip --dest data

    # whole dataset (zip of images)
    python tools/kaggle_download.py \
        --api-path datasets/download/cdeotte/jpeg-melanoma-256x256 \
        --out data/img256.zip --unzip --dest data

    # what slugs exist?
    python tools/kaggle_download.py --list-datasets "melanoma 256"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

API = "https://www.kaggle.com/api/v1"
UA = "melanoma-calib/1.0 (local run guide)"
CHUNK = 1 << 20


def read_token(args) -> str:
    if args.token:
        return args.token.strip()
    env = os.environ.get("KAGGLE_API_TOKEN")
    if env:
        return env.strip()
    path = args.token_file
    if path and os.path.exists(path):
        if os.path.isdir(path):
            sys.exit(f"{path} 是文件夹不是文件（这正是 kaggle CLI 报 WinError 5 的同类问题）。")
        tok = open(path, "r", encoding="utf-8-sig").read().strip()
        if tok:
            return tok
    sys.exit("没有令牌：用 --token、--token-file，或设环境变量 KAGGLE_API_TOKEN")


def request(path_or_url: str, token: str, extra_headers=None):
    url = path_or_url if path_or_url.startswith("http") else f"{API}/{path_or_url.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}", "User-Agent": UA}
    if extra_headers:
        headers.update(extra_headers)
    return urllib.request.Request(url, headers=headers)


def explain(code: int, what: str) -> str:
    if code == 401:
        return ("401 Unauthorized：令牌无效或已撤销。到 https://www.kaggle.com/settings/api "
                "重新 Generate New Token，确认只复制了 KGAT_ 那一行。")
    if code == 403:
        return (f"403 Forbidden：没有权限访问 {what}。多半是没在比赛/数据集页面点 "
                "Join / Accept Rules，或该数据集是私有的。")
    if code == 404:
        return (f"404 Not Found：{what} 不存在（owner/slug 拼错，或已下架）。"
                "用 --list-datasets \"melanoma\" 看看现在的名字。")
    return f"HTTP {code}：{what} 下载失败。"


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def download(args, token: str) -> str:
    what = args.api_path
    start_at = 0
    if args.resume and os.path.exists(args.out):
        start_at = os.path.getsize(args.out)
        print(f"resume from {human(start_at)}")
    headers = {"Range": f"bytes={start_at}-"} if start_at else None

    try:
        resp = urllib.request.urlopen(request(args.api_path, token, headers), timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code == 416:                      # already complete
            print("already fully downloaded")
            return args.out
        sys.exit(explain(exc.code, what))
    except urllib.error.URLError as exc:
        sys.exit(f"网络错误：{exc.reason}。检查代理/VPN，或换 -Dataset 镜像源。")

    total = int(resp.headers.get("Content-Length") or 0) + start_at
    mode = "ab" if start_at and resp.status == 206 else "wb"
    if mode == "wb":
        start_at = 0
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    done, t0, last = start_at, time.time(), 0.0
    with open(args.out, mode, buffering=0) as fh:
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            now = time.time()
            if now - last > 1.0:
                last = now
                rate = (done - start_at) / max(now - t0, 1e-9)
                if total:
                    pct = 100.0 * done / total
                    eta = (total - done) / max(rate, 1e-9) / 60
                    print(f"\r{pct:5.1f}%  {human(done)}/{human(total)}  "
                          f"{human(rate)}/s  eta {eta:.1f} min", end="", flush=True)
                else:
                    print(f"\r{human(done)}  {human(rate)}/s", end="", flush=True)
    print()
    size = os.path.getsize(args.out)
    print(f"saved {args.out}  ({human(size)})")
    return args.out


def unzip(path: str, dest: str, keep: bool):
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        print(f"extracting {len(names)} entries -> {dest}")
        zf.extractall(dest)
    if not keep:
        os.remove(path)
        print(f"removed {path}")


def list_datasets(args, token: str):
    q = urllib.parse.urlencode({"search": args.list_datasets, "page": 1})
    try:
        with urllib.request.urlopen(request(f"datasets/list?{q}", token), timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        sys.exit(explain(exc.code, "datasets/list"))
    print(f"{'ref':52s} {'size':>10s}  title")
    for d in data[:30]:
        ref = d.get("ref", "?")
        size = human(float(d.get("totalBytes") or 0))
        print(f"{ref:52s} {size:>10s}  {(d.get('title') or '')[:60]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-path", help="例 datasets/download/owner/slug 或 "
                                      "competitions/data/download/<comp>/<file>")
    ap.add_argument("--out", help="保存到哪个文件（.zip 或原始文件名）")
    ap.add_argument("--unzip", action="store_true", help="下载后解压")
    ap.add_argument("--dest", default=".", help="解压目标目录（默认当前目录）")
    ap.add_argument("--keep-zip", action="store_true", help="解压后保留 zip")
    ap.add_argument("--resume", action="store_true", help="断点续传（30 GB 下载很有用）")
    ap.add_argument("--token")
    ap.add_argument("--token-file", default=None)
    ap.add_argument("--list-datasets", default=None, help="按关键词搜索数据集，不下载")
    args = ap.parse_args()

    token = read_token(args)
    if args.list_datasets is not None:
        list_datasets(args, token)
        return
    if not args.api_path or not args.out:
        ap.error("需要 --api-path 与 --out（或用 --list-datasets）")

    path = download(args, token)
    if args.unzip:
        unzip(path, args.dest, args.keep_zip)


if __name__ == "__main__":
    main()
