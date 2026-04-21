#!/usr/bin/env python3
"""
upload_itol.py — Upload generated iTOL annotation datasets to the iTOL web service.

Usage:
    python scripts/upload_itol.py [--dir out/itol] [--tree-id YOUR_TREE_ID]

Requires environment variable:
    ITOL_API_KEY   — your iTOL API key
    ITOL_TREE_ID   — tree ID to attach datasets to (or pass via --tree-id)

iTOL batch uploader API: https://itol.embl.de/help.cgi#batchAnnot
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import uuid
from pathlib import Path

try:
    import urllib.request as urlrequest
except ImportError as exc:
    print(f"ERROR: missing stdlib module: {exc}", file=sys.stderr)
    sys.exit(1)


ITOL_ANNOTATE_URL = "https://itol.embl.de/batch_uploader.cgi"


def _multipart_body(fields: dict, files: list) -> tuple:
    """Build a multipart/form-data body.
    files: list of (field_name, filename, file_bytes)
    Returns (body_bytes, content_type_header_value).
    """
    boundary = uuid.uuid4().hex
    ctype = f"multipart/form-data; boundary={boundary}"
    buf = io.BytesIO()
    enc = boundary.encode()

    for name, value in fields.items():
        buf.write(b"--" + enc + b"\r\n")
        buf.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        buf.write(str(value).encode() + b"\r\n")

    for field_name, filename, file_bytes in files:
        buf.write(b"--" + enc + b"\r\n")
        buf.write(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
        )
        buf.write(b"Content-Type: text/plain\r\n\r\n")
        buf.write(file_bytes + b"\r\n")

    buf.write(b"--" + enc + b"--\r\n")
    return buf.getvalue(), ctype


def upload_datasets(api_key: str, tree_id: str, dataset_dir: Path) -> None:
    txt_files = sorted(dataset_dir.glob("dataset_*.txt"))
    if not txt_files:
        print(f"[warn] No dataset_*.txt files found in {dataset_dir}", file=sys.stderr)
        return

    for path in txt_files:
        print(f"  Uploading: {path.name} ...", end=" ", flush=True)
        file_bytes = path.read_bytes()

        fields = {"APIkey": api_key, "treeID": tree_id}
        files = [("datafile", path.name, file_bytes)]
        body, ctype = _multipart_body(fields, files)

        req = urlrequest.Request(
            ITOL_ANNOTATE_URL,
            data=body,
            headers={"Content-Type": ctype},
        )
        try:
            with urlrequest.urlopen(req, timeout=60) as resp:
                reply = resp.read().decode("utf-8", errors="replace").strip()
            if reply.startswith("SUCCESS"):
                print("OK")
            else:
                print(f"FAIL — {reply}")
        except Exception as exc:
            print(f"ERROR — {exc}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Upload iTOL annotation datasets")
    parser.add_argument("--dir", default="out/itol", help="Directory containing dataset_*.txt files")
    parser.add_argument("--tree-id", default="", help="iTOL tree ID (overrides ITOL_TREE_ID env var)")
    args = parser.parse_args(argv)

    api_key = os.getenv("ITOL_API_KEY", "").strip()
    tree_id = (args.tree_id or os.getenv("ITOL_TREE_ID", "")).strip()

    if not api_key:
        print("ERROR: set ITOL_API_KEY environment variable before uploading.", file=sys.stderr)
        return 1
    if not tree_id:
        print("ERROR: set ITOL_TREE_ID environment variable or pass --tree-id.", file=sys.stderr)
        return 1

    dataset_dir = Path(args.dir)
    if not dataset_dir.is_dir():
        print(f"ERROR: directory not found: {dataset_dir}", file=sys.stderr)
        return 1

    print(f"Uploading datasets from {dataset_dir} to iTOL tree {tree_id} ...")
    upload_datasets(api_key, tree_id, dataset_dir)
    print("Upload complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
