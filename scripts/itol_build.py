#!/usr/bin/env python3
"""
itol_build.py — Build iTOL dataset files from an Auspice v2 JSON.

Usage:
    python scripts/itol_build.py \\
        --auspice Example/auspice.json \\
        --plugins labels popup_pymol_links introductions_country mutation_summary attributes_strips \\
        --focal-country "United Arab Emirates" \\
        --focal-abbr UAE \\
        --min-conf 0.8 \\
        --pdb-baseurl "https://github.com/nihlamadala/augur2itol/releases/download/v0.1-demo" \\
        --viewer-url "https://your-netlify-site.netlify.app/viewer.html" \\
        --epitope-tsv data/epitopes_flu_b_ha.tsv \\
        --out out/itol
"""
import argparse
import csv
import importlib
import json
import sys
from pathlib import Path


def _build_parent_map(node, parent=None, pm=None):
    """Build a dict mapping node name -> parent node object."""
    if pm is None:
        pm = {}
    name = node.get("name")
    if name:
        pm[name] = parent
    for child in node.get("children", []):
        _build_parent_map(child, node, pm)
    return pm


def _collect_nodes(node, leaves=None, internals=None):
    """Collect all leaf and internal nodes from the tree."""
    if leaves is None:
        leaves = []
    if internals is None:
        internals = []
    if "children" in node:
        internals.append(node)
        for child in node["children"]:
            _collect_nodes(child, leaves, internals)
    else:
        leaves.append(node)
    return leaves, internals


def _load_epitopes(epitope_path):
    """Load epitope definitions from a TSV file.

    Expected columns: gene, epitope, aa_start, aa_end (plus optional source/notes).
    Lines starting with '#' are treated as comments and skipped.
    Returns: dict mapping gene -> list of {name, start, end} dicts.
    """
    epitopes = {}
    path = Path(epitope_path)
    if not path.exists():
        print(f"WARNING: epitope TSV not found: {path}", file=sys.stderr)
        return epitopes
    with open(path, newline="", encoding="utf-8") as fh:
        # Filter out comment lines before passing to DictReader
        non_comment_lines = (ln for ln in fh if not ln.lstrip().startswith("#"))
        reader = csv.DictReader(non_comment_lines, delimiter="\t")
        for row in reader:
            gene = row.get("gene", "").strip()
            name = row.get("epitope", row.get("name", "")).strip()
            try:
                start = int(row.get("aa_start", row.get("start", 0)))
                end = int(row.get("aa_end", row.get("end", 0)))
            except (ValueError, TypeError):
                continue
            if gene and name:
                epitopes.setdefault(gene, []).append(
                    {"name": name, "start": start, "end": end}
                )
    return epitopes


def main():
    parser = argparse.ArgumentParser(
        description="Build iTOL datasets from an Auspice v2 JSON file."
    )
    parser.add_argument(
        "--auspice", required=True, help="Path to Auspice v2 JSON file"
    )
    parser.add_argument(
        "--plugins",
        nargs="+",
        default=["labels", "popup_pymol_links"],
        help="Plugin names to run (from itol_plugins/ directory)",
    )
    parser.add_argument(
        "--focal-country",
        default="United Arab Emirates",
        help="Full country name for introduction detection (default: United Arab Emirates)",
    )
    parser.add_argument(
        "--focal-abbr",
        default="UAE",
        help="Short abbreviation used in output file names (default: UAE)",
    )
    parser.add_argument(
        "--min-conf",
        type=float,
        default=0.8,
        help="Minimum country confidence threshold for introduction events (default: 0.8)",
    )
    parser.add_argument(
        "--pdb-baseurl",
        default="",
        help="Base URL for PDB files (e.g. GitHub Release asset URL prefix)",
    )
    parser.add_argument(
        "--viewer-url",
        default="",
        help="Base URL for 3D structure viewer page (e.g. Netlify deployment URL)",
    )
    parser.add_argument(
        "--epitope-tsv",
        default="",
        help="Path to TSV file with epitope definitions (gene/epitope/aa_start/aa_end)",
    )
    parser.add_argument(
        "--out",
        default="out/itol",
        help="Output directory for iTOL dataset files (default: out/itol)",
    )
    args = parser.parse_args()

    auspice_path = Path(args.auspice)
    if not auspice_path.exists():
        print(f"ERROR: auspice file not found: {auspice_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(auspice_path.read_text(encoding="utf-8"))
    tree_root = data.get("tree", {})
    meta = data.get("meta", {})
    leaves, internals = _collect_nodes(tree_root)
    parent_map = _build_parent_map(tree_root)

    # Load epitope definitions if provided
    epitopes = {}
    if args.epitope_tsv:
        epitopes = _load_epitopes(args.epitope_tsv)

    ctx = {
        "data": data,
        "tree_root": tree_root,
        "meta": meta,
        "leaves": leaves,
        "internals": internals,
        "all_nodes": leaves + internals,
        "parent_map": parent_map,
        "focal_country": args.focal_country,
        "focal_abbr": args.focal_abbr,
        "min_conf": args.min_conf,
        "pdb_baseurl": args.pdb_baseurl.rstrip("/"),
        "viewer_url": args.viewer_url.rstrip("/"),
        "epitopes": epitopes,
        "genome_annotations": meta.get("genome_annotations", {}),
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Ensure itol_plugins is importable from repo root
    repo_root = str(Path(__file__).parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    written = []
    for plugin_name in args.plugins:
        try:
            mod = importlib.import_module(f"itol_plugins.{plugin_name}")
        except ImportError as exc:
            print(
                f"ERROR: could not import plugin '{plugin_name}': {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

        if not hasattr(mod, "generate"):
            print(
                f"ERROR: plugin '{plugin_name}' has no generate() function",
                file=sys.stderr,
            )
            sys.exit(1)

        result = mod.generate(ctx)
        if not isinstance(result, dict):
            print(
                f"ERROR: plugin '{plugin_name}' generate() must return a dict",
                file=sys.stderr,
            )
            sys.exit(1)

        for fname, content in result.items():
            fpath = out_dir / fname
            fpath.write_text(content, encoding="utf-8")
            written.append(str(fpath))

    print("Wrote files:")
    for f in written:
        print(f" - {f}")
    print(f"Leaves: {len(leaves)}  Internals: {len(internals)}")


if __name__ == "__main__":
    main()
