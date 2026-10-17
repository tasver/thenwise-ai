"""Download weights from Hugging Face to RunPod Global Volume.

Global Volumes are object-backed: do NOT use os.replace/rename, locks or
symlinks on the mount. A .sha256 marker is written only on a verified copy.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path("/workspace-global/models")
MANIFEST = Path(__file__).resolve().parent.parent / "config/model_manifest.json"

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def save_verified(source, dest, expected):
    dest.parent.mkdir(parents=True, exist_ok=True)
    stamp = dest.parent / (dest.name + ".sha256")
    stamp.unlink(missing_ok=True)
    h = hashlib.sha256()
    with open(source, "rb") as src, open(dest, "wb") as dst:
        while chunk := src.read(8 * 1024 * 1024):
            dst.write(chunk)
            h.update(chunk)
    if h.hexdigest() != expected:
        raise RuntimeError(f"Checksum mismatch copying {dest}")
    # No atomic rename: write marker only after content copy succeeds.
    stamp.write_text(expected + "\n", encoding="ascii")

def ready(dest, minimum):
    stamp = dest.parent / (dest.name + ".sha256")
    if not (dest.is_file() and stamp.is_file() and dest.stat().st_size >= minimum):
        return False
    expected = stamp.read_text(encoding="ascii").strip()
    return len(expected) == 64 and sha256(dest) == expected

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=["ltx", "h3", "yue", "all"], default="ltx")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not ROOT.parent.is_dir():
        raise RuntimeError("Global Volume missing: mount at /workspace-global")
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    for item in rows:
        if args.group not in ("all", item["group"]):
            continue
        dst = ROOT / item["dest"]
        minimum = int(item["min_gib"] * 1024**3)
        if args.list:
            print(item, flush=True)
            continue
        if ready(dst, minimum):
            print("VERIFIED", dst, flush=True)
            continue
        if args.verify_only:
            raise RuntimeError(f"Missing or unverified: {dst}")
        print("DOWNLOAD", item["repo"], item["remote"], flush=True)
        src = Path(hf_hub_download(
            repo_id=item["repo"],
            filename=item["remote"],
            cache_dir="/workspace/cache/hf",
            token=os.environ.get("HF_TOKEN"),
        ))
        if src.stat().st_size < minimum:
            raise RuntimeError(f"Downloaded model unexpectedly small: {src}")
        expected = sha256(src)
        save_verified(src, dst, expected)
        print("SAVED", dst, flush=True)

if __name__ == "__main__":
    main()
