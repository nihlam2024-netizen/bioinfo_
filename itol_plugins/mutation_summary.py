"""
mutation_summary.py — iTOL DATASET_HEATMAP plugin.

Generates a heatmap showing the total branch-specific mutation count for every
leaf node.  Nucleotide and amino-acid mutations are summed together as a simple
proxy for evolutionary distance from the parent.
"""
from __future__ import annotations

from typing import List, Tuple


def _extract_mutations(node: dict) -> Tuple[List[str], List[str]]:
    """Return (nuc_list, aa_list) for a single node's branch_attrs."""
    ba = (node or {}).get("branch_attrs", {}) or {}
    muts = ba.get("mutations") or {}
    nuc: List[str] = []
    aa: List[str] = []

    if isinstance(muts, dict):
        raw_nuc = muts.get("nuc")
        if isinstance(raw_nuc, list):
            nuc = list(raw_nuc)

        aa_obj = muts.get("aa")
        if isinstance(aa_obj, dict):
            for prot, changes in aa_obj.items():
                if isinstance(changes, list):
                    for c in changes:
                        aa.append(f"{prot}:{c}")
        elif isinstance(aa_obj, list):
            aa = list(aa_obj)

    return nuc, aa


def generate(ctx: dict) -> dict:
    """
    Build an iTOL DATASET_HEATMAP file with one column: 'mut_count'.

    The value for each leaf equals len(nuc_muts) + len(aa_muts) on that
    specific branch.  Internal-node accumulation is NOT included — this
    reflects only the mutations on the terminal branch.
    """
    leaves = ctx["leaves"]

    lines = [
        "DATASET_HEATMAP",
        "SEPARATOR\tTAB",
        "DATASET_LABEL\tMutation count (branch)",
        "COLOR\t#1f78b4",
        "FIELD_LABELS\tmut_count",
        "FIELD_COLORS\t#1f78b4",
        "COLOR_MIN\t#ffffff",
        "COLOR_MAX\t#1f78b4",
        "DATA",
    ]

    for leaf in leaves:
        leaf_id = leaf["name"]
        nuc, aa = _extract_mutations(leaf)
        mut_count = len(nuc) + len(aa)
        lines.append(f"{leaf_id}\t{mut_count}")

    return {"dataset_mutation_count_heatmap.txt": "\n".join(lines) + "\n"}
