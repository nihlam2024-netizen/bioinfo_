#!/usr/bin/env python3
"""
prune_auspice.py — Prune an Auspice v2 JSON to keep only specified leaves.

An "introduction" context often requires viewing only the focal country's sequences
on a cleaner subtree. This script filters the tree to leaves whose node attribute
matches the requested value(s), pruning empty internal branches automatically.

Usage (UAE example):
    python scripts/prune_auspice.py \\
        --auspice Example/auspice.json \\
        --keep-attr country \\
        --keep-value "United Arab Emirates" \\
        --out out/pruned_uae_auspice.json

Multiple values (keep UAE + Egypt):
    python scripts/prune_auspice.py \\
        --auspice Example/auspice.json \\
        --keep-attr country \\
        --keep-value "United Arab Emirates" "Egypt" \\
        --out out/pruned_me_auspice.json
"""
import argparse
import json
import sys
from pathlib import Path


def _filter_tree(node, keep_attr, keep_values):
    """Recursively filter tree. Returns node if kept, else None."""
    if "children" not in node:
        # Leaf node — keep if attribute value is in keep_values
        val = node.get("node_attrs", {}).get(keep_attr, {}).get("value", None)
        if val in keep_values:
            return node
        return None

    # Internal node: recurse into children
    kept_children = []
    for child in node.get("children", []):
        result = _filter_tree(child, keep_attr, keep_values)
        if result is not None:
            kept_children.append(result)

    if not kept_children:
        return None

    # Return a copy of the node with only the kept children
    new_node = {k: v for k, v in node.items() if k != "children"}
    if len(kept_children) == 1 and "children" in node:
        # Collapse single-child internal nodes (optional; keeps tree readable)
        new_node["children"] = kept_children
    else:
        new_node["children"] = kept_children
    return new_node


def _count_leaves(node):
    """Count leaf nodes in a tree."""
    if "children" not in node:
        return 1
    return sum(_count_leaves(c) for c in node.get("children", []))


def main():
    parser = argparse.ArgumentParser(
        description="Prune Auspice v2 JSON to keep only leaves matching a node attribute."
    )
    parser.add_argument("--auspice", required=True, help="Path to Auspice v2 JSON file")
    parser.add_argument(
        "--keep-attr",
        default="country",
        help="Node attribute key to filter on (default: country)",
    )
    parser.add_argument(
        "--keep-value",
        nargs="+",
        required=True,
        help="Value(s) to keep (e.g. 'United Arab Emirates')",
    )
    parser.add_argument("--out", required=True, help="Output path for pruned JSON file")
    args = parser.parse_args()

    auspice_path = Path(args.auspice)
    if not auspice_path.exists():
        print(f"ERROR: file not found: {auspice_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(auspice_path.read_text(encoding="utf-8"))
    tree_root = data.get("tree", {})
    keep_values = set(args.keep_value)

    original_count = _count_leaves(tree_root)
    pruned = _filter_tree(tree_root, args.keep_attr, keep_values)

    if pruned is None:
        print(
            f"ERROR: no leaves found with {args.keep_attr!r} in {keep_values}",
            file=sys.stderr,
        )
        sys.exit(1)

    kept_count = _count_leaves(pruned)

    out_data = {k: v for k, v in data.items() if k != "tree"}
    out_data["tree"] = pruned

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")

    print(f"Pruned: {original_count} leaves -> {kept_count} leaves kept")
    print(f"Kept attribute '{args.keep_attr}' values: {sorted(keep_values)}")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
