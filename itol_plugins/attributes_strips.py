"""
Plugin: attributes_strips — generate DATASET_COLORSTRIP files for node attributes.

Produces one colour strip per attribute that has at least one data point:
  - country      (pre-defined palette + hash-based fallback)
  - region       (pre-defined palette)
  - clade_membership
  - host
  - severity     (clinical attribute; absent in many datasets)

Colours for known countries/regions use a curated palette; unknown values
are assigned a deterministic colour derived from an MD5 hash of the value
string, ensuring consistent colouring across builds.
"""

import colorsys
import hashlib


# Curated colour palettes for common values
COUNTRY_COLORS = {
    "United Arab Emirates": "#1f78b4",
    "United States": "#33a02c",
    "United Kingdom": "#e31a1c",
    "France": "#ff7f00",
    "Germany": "#6a3d9a",
    "China": "#b15928",
    "Australia": "#a6cee3",
    "Japan": "#b2df8a",
    "India": "#fb9a99",
    "South Africa": "#fdbf6f",
    "Spain": "#cab2d6",
    "Italy": "#ffff99",
    "Russian Federation": "#1a9641",
    "Brazil": "#b3de69",
    "Canada": "#fccde5",
    "Egypt": "#d9d9d9",
    "Saudi Arabia": "#bc80bd",
    "Netherlands": "#ccebc5",
    "Belgium": "#ffed6f",
    "Sweden": "#8dd3c7",
}

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


def _hash_color(value):
    """Generate a deterministic, visually distinct colour from a string value."""
    digest = hashlib.md5(str(value).encode()).hexdigest()
    r = int(digest[0:2], 16) / 255.0
    g = int(digest[2:4], 16) / 255.0
    b = int(digest[4:6], 16) / 255.0
    # Clamp to reasonable brightness/saturation
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = max(0.45, s)
    v = max(0.55, min(0.90, v))
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02x}{:02x}{:02x}".format(int(r2 * 255), int(g2 * 255), int(b2 * 255))


def _build_colorstrip(nodes, attr_key, label, predefined_colors=None):
    """Build a DATASET_COLORSTRIP for a given node attribute.

    Returns the dataset text string, or None if no data is available.
    """
    value_color = {}  # ordered by first appearance
    rows = []

    for node in nodes:
        name = node.get("name", "")
        if not name:
            continue
        val = node.get("node_attrs", {}).get(attr_key, {}).get("value", None)
        if val is None or val == "":
            continue
        val_str = str(val)
        if val_str not in value_color:
            if predefined_colors and val_str in predefined_colors:
                color = predefined_colors[val_str]
            else:
                color = _hash_color(val_str)
            value_color[val_str] = color
        rows.append((name, value_color[val_str], val_str))

    if not rows:
        return None

    legend_items = list(value_color.items())

    lines = [
        "DATASET_COLORSTRIP",
        "SEPARATOR TAB",
        f"DATASET_LABEL\t{label}",
        f"COLOR\t{legend_items[0][1]}",
        f"LEGEND_TITLE\t{label}",
        "LEGEND_SHAPES\t" + "\t".join(["1"] * len(legend_items)),
        "LEGEND_COLORS\t" + "\t".join(c for _, c in legend_items),
        "LEGEND_LABELS\t" + "\t".join(v for v, _ in legend_items),
        "DATA",
    ]
    for name, color, val in rows:
        lines.append(f"{name}\t{color}\t{val}")

    return "\n".join(lines) + "\n"


def generate(ctx):
    all_nodes = ctx["all_nodes"]
    results = {}

    # Country colour strip
    cs = _build_colorstrip(all_nodes, "country", "Country", COUNTRY_COLORS)
    if cs:
        results["dataset_country_strip.txt"] = cs

    # Region colour strip
    rs = _build_colorstrip(all_nodes, "region", "Region", REGION_COLORS)
    if rs:
        results["dataset_region_strip.txt"] = rs

    # Clade colour strip
    cl = _build_colorstrip(all_nodes, "clade_membership", "Clade")
    if cl:
        results["dataset_clade_strip.txt"] = cl

    # Host colour strip
    hs = _build_colorstrip(all_nodes, "host", "Host")
    if hs:
        results["dataset_host_strip.txt"] = hs

    # Severity colour strip (clinical; often absent)
    sv = _build_colorstrip(all_nodes, "severity", "Severity")
    if sv:
        results["dataset_severity_strip.txt"] = sv

    return results
