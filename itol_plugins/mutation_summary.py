"""
Plugin: mutation_summary — generate a DATASET_HEATMAP of per-node mutation counts.

Outputs two columns:
  - Nuc_Muts: number of nucleotide mutations on the branch leading to this node
  - AA_Muts:  total number of amino-acid mutations across all genes on this branch

Counts are taken from branch_attrs.mutations in the Auspice JSON (mutations
relative to the parent node, not cumulative from root).

Use this dataset in iTOL to visualize relative divergence across the tree.
"""


def _get_mutation_counts(node):
    """Return (nuc_count, aa_count) for a node's branch mutations."""
    branch = node.get("branch_attrs", {}).get("mutations", {})
    nuc_count = len(branch.get("nuc", []))
    aa_count = sum(len(v) for k, v in branch.items() if k != "nuc")
    return nuc_count, aa_count


def generate(ctx):
    all_nodes = ctx["all_nodes"]

    rows = []
    for node in all_nodes:
        name = node.get("name", "")
        if not name:
            continue
        nuc, aa = _get_mutation_counts(node)
        if nuc > 0 or aa > 0:
            rows.append((name, nuc, aa))

    if not rows:
        # Return an empty-but-valid file so the build doesn't fail
        lines = [
            "DATASET_HEATMAP",
            "SEPARATOR TAB",
            "DATASET_LABEL\tMutation Counts",
            "COLOR\t#1f78b4",
            "COLOR_MIN\t#ffffff",
            "COLOR_MAX\t#1f78b4",
            "FIELD_LABELS\tNuc_Muts\tAA_Muts",
            "FIELD_COLORS\t#33a02c\t#e31a1c",
            "DATA",
        ]
        return {"dataset_mutation_counts.txt": "\n".join(lines) + "\n"}

    lines = [
        "DATASET_HEATMAP",
        "SEPARATOR TAB",
        "DATASET_LABEL\tMutation Counts",
        "COLOR\t#1f78b4",
        "COLOR_MIN\t#ffffff",
        "COLOR_MAX\t#1f78b4",
        "FIELD_LABELS\tNuc_Muts\tAA_Muts",
        "FIELD_COLORS\t#33a02c\t#e31a1c",
        "DATA",
    ]

    for name, nuc, aa in rows:
        lines.append(f"{name}\t{nuc}\t{aa}")

    return {"dataset_mutation_counts.txt": "\n".join(lines) + "\n"}
