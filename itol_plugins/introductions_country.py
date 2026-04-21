"""
Plugin: introductions_country — detect virus introduction events into a focal country.

An introduction event is defined as:
  - The node's inferred country == focal_country
  - The node's parent's inferred country != focal_country
  - The node's country confidence[focal_country] >= min_conf

This applies to both leaf nodes (sampled sequences) and internal nodes
(inferred ancestral states).

CLI parameters (passed via itol_build.py context):
  focal_country  Full country name, e.g. "United Arab Emirates"
  focal_abbr     Short abbreviation for file name, e.g. "UAE"
  min_conf       Confidence threshold, default 0.8

Output: DATASET_COLORSTRIP — marks each introduction node in red with a
label showing the inferred origin country and confidence value.
"""

STRIP_COLOR = "#e41a1c"


def _node_name(node):
    return node.get("name", "")


def _country_value(node):
    if node is None:
        return None
    return node.get("node_attrs", {}).get("country", {}).get("value", None)


def _confidence_for(node, country):
    if node is None:
        return None
    return (
        node.get("node_attrs", {})
        .get("country", {})
        .get("confidence", {})
        .get(country, None)
    )


def generate(ctx):
    focal_country = ctx["focal_country"]
    focal_abbr = ctx["focal_abbr"]
    min_conf = ctx["min_conf"]
    parent_map = ctx["parent_map"]
    all_nodes = ctx["all_nodes"]

    introductions = {}

    for node in all_nodes:
        name = _node_name(node)
        if not name:
            continue

        # Node must be assigned to the focal country
        c = _country_value(node)
        if c != focal_country:
            continue

        # Confidence for focal country must meet threshold
        conf = _confidence_for(node, focal_country)
        if conf is None or conf < min_conf:
            continue

        # Parent must be from a different country (or no parent = root)
        parent = parent_map.get(name)
        parent_c = _country_value(parent) if parent else None
        if parent_c == focal_country:
            continue  # same country as parent — not a new introduction

        introductions[name] = (conf, parent_c)

    lines = [
        "DATASET_COLORSTRIP",
        "SEPARATOR TAB",
        f"DATASET_LABEL\tIntroductions to {focal_abbr}",
        f"COLOR\t{STRIP_COLOR}",
        "LEGEND_TITLE\tIntroductions",
        "LEGEND_SHAPES\t1",
        f"LEGEND_COLORS\t{STRIP_COLOR}",
        f"LEGEND_LABELS\tIntro to {focal_abbr} (conf>={min_conf})",
        "DATA",
    ]

    for node_id, (conf, parent_c) in sorted(introductions.items()):
        label = f"Intro (from {parent_c or 'NA'}, conf={conf:.3f})"
        lines.append(f"{node_id}\t{STRIP_COLOR}\t{label}")

    fname = f"dataset_introductions_{focal_abbr}.txt"
    return {fname: "\n".join(lines) + "\n"}
