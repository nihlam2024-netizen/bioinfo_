"""
labels.py — iTOL DATASET_TEXT plugin: simple leaf-node labels.

For each leaf in the tree, emits a text label dataset that iTOL can display
at the tip.  Falls back to the node name if no 'strain' attribute is present.
"""
from __future__ import annotations


def generate(ctx: dict) -> dict:
    """
    Generate an iTOL DATASET_TEXT file containing one label per leaf.

    Returns
    -------
    dict
        {"dataset_labels.txt": <file content as str>}
    """
    leaves = ctx["leaves"]
    get_attr = ctx["get_attr"]

    lines = [
        "DATASET_TEXT",
        "SEPARATOR TAB",
        "DATASET_LABEL\tLeaf labels",
        "COLOR\t#000000",
        "MARGIN\t5",
        "SIZE_FACTOR\t1",
        "DATA",
    ]

    for leaf in leaves:
        leaf_id = leaf["name"]
        label = get_attr(leaf, "strain", "") or leaf_id
        # size_factor, color, style, rotation, shift, position (all optional after the value)
        lines.append(f"{leaf_id}\t{label}\t1\t#000000\tnormal\t0")

    return {"dataset_labels.txt": "\n".join(lines) + "\n"}
