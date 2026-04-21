"""
attributes_strips.py — iTOL DATASET_COLORSTRIP plugin.

Generates one COLORSTRIP dataset per configured attribute (region, clade, country,
division).  Colour palettes are assigned automatically using a deterministic
hash-based scheme so the same value always gets the same colour.
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

# Predefined palette for up to 12 categories per attribute (beyond 12 we hash)
_PALETTE = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
    "#ff7f00", "#a65628", "#f781bf", "#999999",
    "#1b9e77", "#d95f02", "#7570b3", "#e7298a",
]


def _color_for(value: str, palette_index: Dict[str, str]) -> str:
    """Return the colour assigned to *value*, creating one if needed."""
    if value not in palette_index:
        idx = len(palette_index)
        if idx < len(_PALETTE):
            palette_index[value] = _PALETTE[idx]
        else:
            # Hash-based fallback: deterministic hex colour
            h = hashlib.md5(value.encode()).hexdigest()
            palette_index[value] = f"#{h[:6]}"
    return palette_index[value]


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

# Attributes to generate strips for (in order)
_STRIP_ATTRS: List[str] = ["region", "country", "clade", "division"]


def generate(ctx: dict) -> dict:
    """
    Build one DATASET_COLORSTRIP file per configured attribute.

    Returns
    -------
    dict
        {filename: content_str, ...} — one entry per attribute.
    """
    leaves = ctx["leaves"]
    get_attr = ctx["get_attr"]

    outputs: Dict[str, str] = {}

    for attr in _STRIP_ATTRS:
        palette_index: Dict[str, str] = {}
        data_rows: List[str] = []

        for leaf in leaves:
            leaf_id = leaf["name"]
            value = str(get_attr(leaf, attr, "unknown") or "unknown")
            color = _color_for(value, palette_index)
            data_rows.append(f"{leaf_id}\t{color}\t{value}")

        # Build legend entries
        legend_shapes = "\t".join("1" for _ in palette_index)
        legend_colors = "\t".join(palette_index[v] for v in palette_index)
        legend_labels = "\t".join(palette_index.keys())

        lines = [
            "DATASET_COLORSTRIP",
            "SEPARATOR\tTAB",
            f"DATASET_LABEL\t{attr.capitalize()}",
            f"COLOR\t{next(iter(palette_index.values()), '#888888')}",
            "LEGEND_TITLE\t" + attr.capitalize(),
            f"LEGEND_SHAPES\t{legend_shapes}",
            f"LEGEND_COLORS\t{legend_colors}",
            f"LEGEND_LABELS\t{legend_labels}",
            "DATA",
        ] + data_rows

        fname = f"dataset_strip_{attr}.txt"
        outputs[fname] = "\n".join(lines) + "\n"

    return outputs
