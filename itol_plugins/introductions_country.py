"""
introductions_country.py — iTOL DATASET_COLORSTRIP plugin.

Marks leaf nodes that represent introductions into a focal country based on
inferred country transitions and a per-node confidence threshold.

Environment variables
---------------------
ITOL_FOCAL_COUNTRY  : country label to track introductions *into* (default: UAE)
ITOL_INTRO_MIN_CONF : minimum confidence in focal-country assignment (default: 0.8)
"""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _country_value(node) -> Optional[str]:
    na = (node or {}).get("node_attrs") or {}
    c = na.get("country") or {}
    return c.get("value")


def _country_confidence_map(node) -> Dict[str, float]:
    na = (node or {}).get("node_attrs") or {}
    c = na.get("country") or {}
    conf = c.get("confidence") or {}
    out: Dict[str, float] = {}
    for k, v in conf.items():
        try:
            out[k] = float(v)
        except Exception:
            continue
    return out


def _confidence_for(node, focal_country: str) -> Optional[float]:
    return _country_confidence_map(node).get(focal_country)


def _node_name(node) -> Optional[str]:
    return node.get("name")


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def generate(ctx: dict) -> dict:
    """
    Build a COLORSTRIP dataset marking every leaf that is an introduction into
    *focal_country* (i.e. its inferred country is focal_country but its parent's
    is not, and the confidence meets *min_conf*).
    """
    tree = ctx["tree"]

    focal_country = ctx.get("focal_country") or os.getenv("ITOL_FOCAL_COUNTRY", "UAE").strip() or "UAE"
    min_conf_raw = ctx.get("min_conf")
    try:
        min_conf = float(min_conf_raw) if min_conf_raw is not None else float(os.getenv("ITOL_INTRO_MIN_CONF", "0.8"))
    except Exception:
        min_conf = 0.8

    strip_color = "#e41a1c"
    introductions: Dict[str, Tuple[float, Optional[str]]] = {}

    stack = [(tree, None)]
    while stack:
        node, parent = stack.pop()
        for ch in node.get("children", []) or []:
            stack.append((ch, node))

        # Only mark leaf nodes (actual sampled sequences, not ancestral nodes)
        if node.get("children"):
            continue

        name = _node_name(node)
        if not name:
            continue

        c = _country_value(node)
        if c != focal_country:
            continue

        parent_c = _country_value(parent) if parent else None
        if parent_c == focal_country:
            continue  # not a new introduction

        conf = _confidence_for(node, focal_country)
        if conf is None or conf < min_conf:
            continue

        introductions[name] = (conf, parent_c)

    lines = []
    lines.append("DATASET_COLORSTRIP")
    lines.append("SEPARATOR\tTAB")
    lines.append(f"DATASET_LABEL\tIntroductions to {focal_country}")
    lines.append(f"COLOR\t{strip_color}")
    lines.append("LEGEND_TITLE\tIntroductions")
    lines.append("LEGEND_SHAPES\t1")
    lines.append(f"LEGEND_COLORS\t{strip_color}")
    lines.append(f"LEGEND_LABELS\tIntro to {focal_country} (conf>={min_conf})")
    lines.append("DATA")

    for node_id, (conf, parent_c) in sorted(introductions.items()):
        label = f"Intro (from {parent_c or 'NA'}, conf={conf:.3f})"
        lines.append(f"{node_id}\t{strip_color}\t{label}")

    fname = f"dataset_introductions_{focal_country}.txt"
    return {fname: "\n".join(lines) + "\n"}
