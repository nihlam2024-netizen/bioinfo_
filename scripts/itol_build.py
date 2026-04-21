#!/usr/bin/env python3
"""
itol_build.py — Build iTOL annotation datasets from an Augur/Nextstrain auspice.json.

Usage:
    python scripts/itol_build.py \\
        --auspice Example/auspice.json \\
        --plugins labels introductions_country popup_pymol_links mutation_summary \\
        --epitope-tsv data/epitopes_flu_b_ha.tsv \\
        --out out/itol
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Tree utilities
# ---------------------------------------------------------------------------

def _walk(node: dict, parent: Optional[dict] = None):
    """DFS walk of the tree; yields (node, parent) pairs."""
    yield node, parent
    for child in node.get("children", []) or []:
        yield from _walk(child, node)


def _partition(tree_root: dict) -> Tuple[List[dict], List[dict]]:
    """Return (leaves, internals)."""
    leaves: List[dict] = []
    internals: List[dict] = []
    for node, _ in _walk(tree_root):
        if node.get("children"):
            internals.append(node)
        else:
            leaves.append(node)
    return leaves, internals


def _parent_map(tree_root: dict) -> Dict[str, str]:
    """Return mapping from child node name -> parent node name."""
    pm: Dict[str, str] = {}
    for node, parent in _walk(tree_root, None):
        name = node.get("name")
        pname = parent.get("name") if parent else None
        if name and pname:
            pm[name] = pname
    return pm


# ---------------------------------------------------------------------------
# Attribute helper
# ---------------------------------------------------------------------------

def make_get_attr(leaves: List[dict]):
    """Return a get_attr(node, key, default='') helper."""

    def get_attr(node: dict, key: str, default: Any = "") -> Any:
        attrs = (node or {}).get("node_attrs", {}) or {}
        v = attrs.get(key)
        if isinstance(v, dict):
            val = v.get("value")
            return default if val is None else val
        return default if v is None else v

    return get_attr


# ---------------------------------------------------------------------------
# Epitope loading
# ---------------------------------------------------------------------------

def _load_epitopes(path: str) -> List[dict]:
    """
    Load epitope TSV.  Expected columns (tab-separated, with header):
        name, start, end, [color], [description]
    """
    rows: List[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            header: Optional[List[str]] = None
            for line in fh:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if header is None:
                    header = [h.lower() for h in parts]
                    continue
                row = dict(zip(header, parts))
                # Coerce numeric fields
                for field in ("start", "end"):
                    if field in row:
                        try:
                            row[field] = int(row[field])
                        except ValueError:
                            pass
                rows.append(row)
    except FileNotFoundError:
        print(f"[warn] Epitope file not found: {path}", file=sys.stderr)
    return rows


# ---------------------------------------------------------------------------
# Plugin loader
# ---------------------------------------------------------------------------

def _load_plugin(name: str):
    """Import itol_plugins/<name>.py and return the module."""
    plugins_parent = Path(__file__).resolve().parent.parent
    plugins_dir = plugins_parent / "itol_plugins"

    if str(plugins_parent) not in sys.path:
        sys.path.insert(0, str(plugins_parent))

    try:
        return importlib.import_module(f"itol_plugins.{name}")
    except ModuleNotFoundError:
        # Fallback: add the plugins directory itself to path and import by bare name
        if str(plugins_dir) not in sys.path:
            sys.path.insert(0, str(plugins_dir))
        return importlib.import_module(name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build iTOL annotation datasets from an Augur auspice.json"
    )
    parser.add_argument("--auspice", required=True, help="Path to auspice.json")
    parser.add_argument(
        "--plugins",
        nargs="+",
        default=["labels"],
        help="Plugin module names (itol_plugins/*.py)",
    )
    parser.add_argument("--epitope-tsv", default=None, help="Path to epitope TSV file")
    parser.add_argument("--out", default="out/itol", help="Output directory")
    parser.add_argument("--pdb-baseurl", default="", help="Base URL for PDB structure files")
    parser.add_argument("--viewer-url", default="", help="URL for 3D structure viewer page")
    args = parser.parse_args(argv)

    # Load auspice.json
    auspice_path = Path(args.auspice)
    if not auspice_path.exists():
        print(f"ERROR: auspice.json not found: {auspice_path}", file=sys.stderr)
        return 1
    data: Dict[str, Any] = json.loads(auspice_path.read_text(encoding="utf-8"))

    # Parse tree
    tree_root: dict = data.get("tree") or {}
    meta: dict = data.get("meta") or {}
    leaves, internals = _partition(tree_root)
    all_nodes = leaves + internals
    pm = _parent_map(tree_root)
    genome_annotations: dict = meta.get("genome_annotations", {}) or {}

    # Load epitopes
    epitopes = _load_epitopes(args.epitope_tsv) if args.epitope_tsv else []

    # Env-configurable params
    try:
        focal_country = os.getenv("ITOL_FOCAL_COUNTRY", "UAE").strip() or "UAE"
        # Use explicit env var for abbreviation; fall back to first 3 chars (or full name if shorter)
        focal_abbr = os.getenv("ITOL_FOCAL_ABBR", focal_country[:3].upper() if len(focal_country) >= 3 else focal_country.upper())
        min_conf = float(os.getenv("ITOL_INTRO_MIN_CONF", "0.8"))
    except Exception:
        focal_country = "UAE"
        focal_abbr = "UAE"
        min_conf = 0.8

    pdb_baseurl = (args.pdb_baseurl or os.getenv("ITOL_PDB_BASEURL", "")).strip()
    viewer_url = (args.viewer_url or os.getenv("ITOL_VIEWER_URL", "")).strip()

    # Build shared context passed to every plugin
    ctx: Dict[str, Any] = {
        "data": data,
        "tree": tree_root,
        "tree_root": tree_root,
        "meta": meta,
        "leaves": leaves,
        "internals": internals,
        "all_nodes": all_nodes,
        "parent_map": pm,
        "focal_country": focal_country,
        "focal_abbr": focal_abbr,
        "min_conf": min_conf,
        "pdb_baseurl": pdb_baseurl,
        "pdb_map": {},
        "viewer_url": viewer_url,
        "epitopes": epitopes,
        "genome_annotations": genome_annotations,
        "get_attr": make_get_attr(leaves),
    }

    # Output directory
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Run each plugin
    written: List[str] = []
    for plugin_name in args.plugins:
        try:
            mod = _load_plugin(plugin_name)
        except Exception as exc:
            print(f"[error] Could not load plugin '{plugin_name}': {exc}", file=sys.stderr)
            continue

        try:
            result = mod.generate(ctx)
        except Exception as exc:
            print(f"[error] Plugin '{plugin_name}' failed: {exc}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            continue

        if not isinstance(result, dict):
            print(
                f"[warn] Plugin '{plugin_name}' returned {type(result).__name__} instead of dict",
                file=sys.stderr,
            )
            continue

        for fname, content in result.items():
            out_path = out_dir / fname
            out_path.write_text(content, encoding="utf-8")
            written.append(str(out_path))
            print(f"  Wrote: {out_path}")

    print(f"\nDone. {len(written)} file(s) written to {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
