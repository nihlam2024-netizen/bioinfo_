"""
Plugin: tree_colors_region — colour leaf labels by geographic region.

Generates a DATASET_COLORSTRIP with a consistent colour per region,
providing an at-a-glance geographic overview of the phylogenetic tree.
"""

REGION_COLORS = {
    "Asia": "#e41a1c",
    "Europe": "#377eb8",
    "North America": "#4daf4a",
    "South America": "#984ea3",
    "Africa": "#ff7f00",
    "Oceania": "#a65628",
    "Middle East": "#f781bf",
    "Central America": "#999999",
}

DEFAULT_COLOR = "#cccccc"


def generate(ctx):
    leaves = ctx["leaves"]

    seen = {}  # region -> color (ordered by first appearance)
    rows = []

    for leaf in leaves:
        name = leaf.get("name", "")
        region = leaf.get("node_attrs", {}).get("region", {}).get("value", "")
        if not name or not region:
            continue
        color = REGION_COLORS.get(region, DEFAULT_COLOR)
        if region not in seen:
            seen[region] = color
        rows.append(f"{name}\t{color}\t{region}")

    lines = [
        "DATASET_COLORSTRIP",
        "SEPARATOR TAB",
        "DATASET_LABEL\tRegion",
        f"COLOR\t{DEFAULT_COLOR}",
        "LEGEND_TITLE\tRegion",
    ]

    if seen:
        lines.append("LEGEND_SHAPES\t" + "\t".join(["1"] * len(seen)))
        lines.append("LEGEND_COLORS\t" + "\t".join(seen.values()))
        lines.append("LEGEND_LABELS\t" + "\t".join(seen.keys()))

    lines.append("DATA")
    lines.extend(rows)

    return {"dataset_region_colors.txt": "\n".join(lines) + "\n"}
