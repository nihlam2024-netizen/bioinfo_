"""
popup_pymol_links.py — iTOL POPUP_INFO plugin (enriched).

For every leaf, generates a rich HTML popup containing:
  - Core metadata  (region, date, country, division, clade)
  - Introduction inference  (focal-country confidence, intro flag, parent country)
  - Branch-specific mutations  (nucleotide + amino-acid counts and lists)
  - Epitope / annotation mapping  (maps AA mutations onto genome_annotations features
    and, when a TSV is supplied, onto named epitope regions)
  - Structure link  (PDB download + PyMOL / viewer open instructions)

Environment variables
---------------------
ITOL_FOCAL_COUNTRY  : focal country for introduction detection  (default: UAE)
ITOL_INTRO_MIN_CONF : minimum confidence for introduction flag  (default: 0.8)
"""
from __future__ import annotations

import os
from html import escape
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _walk(node: dict, parent: Optional[dict] = None):
    yield node, parent
    for ch in (node.get("children") or []):
        yield from _walk(ch, node)


def _get_attr_obj(node: dict, key: str) -> dict:
    attrs = (node or {}).get("node_attrs", {}) or {}
    v = attrs.get(key)
    return v if isinstance(v, dict) else {}


def _get_value(node: dict, key: str, default: str = "") -> str:
    v = _get_attr_obj(node, key)
    vv = v.get("value")
    return default if vv is None else str(vv)


def _get_conf_map(node: dict, key: str) -> Dict[str, float]:
    v = _get_attr_obj(node, key)
    conf = v.get("confidence") or {}
    return conf if isinstance(conf, dict) else {}


def _fmt_list(xs: list, max_items: int = 25) -> str:
    items = [str(x) for x in xs if x is not None and str(x).strip()]
    if not items:
        return "NA"
    if len(items) <= max_items:
        return ", ".join(items)
    return ", ".join(items[:max_items]) + f", ... (+{len(items) - max_items} more)"


def _extract_mutations(node: dict) -> Tuple[List[str], List[str]]:
    """
    Extract branch-specific mutations from branch_attrs.mutations.
    Returns (nuc_list, aa_list) where aa items are prefixed with 'PROT:'.
    """
    ba = (node or {}).get("branch_attrs", {}) or {}
    muts = ba.get("mutations") or {}
    nuc: List[str] = []
    aa: List[str] = []

    if isinstance(muts, dict):
        # Nucleotide mutations
        raw_nuc = muts.get("nuc")
        if isinstance(raw_nuc, list):
            nuc = list(raw_nuc)

        # AA mutations — two common layouts:
        #   {"aa": {"HA": ["S145N", ...], "NA": [...]}}   (dict-of-lists)
        #   {"aa": ["HA:S145N", ...]}                      (flat list)
        aa_obj = muts.get("aa")
        if isinstance(aa_obj, dict):
            for prot, changes in aa_obj.items():
                if isinstance(changes, list):
                    for c in changes:
                        aa.append(f"{prot}:{c}")
        elif isinstance(aa_obj, list):
            aa = list(aa_obj)

        # Fallback key variants
        for k in ("aa_muts", "aaMutations", "amino_acid"):
            extra = muts.get(k)
            if isinstance(extra, dict):
                for prot, changes in extra.items():
                    if isinstance(changes, list):
                        for c in changes:
                            aa.append(f"{prot}:{c}")
            elif isinstance(extra, list):
                aa.extend(str(x) for x in extra)

    return nuc, aa


def _parse_aa_position(mut_str: str) -> Optional[int]:
    """
    Extract numeric position from a mutation string like 'HA:S145N' or 'S145N'.
    Returns the integer position, or None if not parseable.
    """
    s = mut_str.split(":", 1)[-1]  # strip 'PROT:' prefix
    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
        elif num:
            break
    if num:
        try:
            return int(num)
        except ValueError:
            pass
    return None


def _map_to_epitopes(aa_muts: List[str], epitopes: list) -> List[str]:
    """
    Map AA mutations to named epitope regions from the supplied TSV rows.
    Returns a list of hit region names (deduplicated, order-preserved).
    """
    hits: List[str] = []
    seen = set()
    for m in aa_muts:
        pos = _parse_aa_position(m)
        if pos is None:
            continue
        for ep in epitopes:
            try:
                start = int(ep.get("start", -1))
                end = int(ep.get("end", -1))
            except (TypeError, ValueError):
                continue
            if start <= pos <= end:
                name = ep.get("name") or ep.get("description") or f"site:{start}-{end}"
                if name not in seen:
                    hits.append(name)
                    seen.add(name)
    return hits


def _map_to_annotations(aa_muts: List[str], genome_annotations: dict) -> List[str]:
    """
    Map AA mutations to genome_annotations features.
    Only CDS features with explicit start/end are considered.
    """
    hits: List[str] = []
    seen = set()
    for m in aa_muts:
        # If the mutation is prefixed 'GENE:change', the gene name IS the annotation hit
        if ":" in m:
            gene = m.split(":", 1)[0]
            if gene in genome_annotations and gene not in seen:
                hits.append(f"{gene} (CDS)")
                seen.add(gene)
    return hits


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def generate(ctx: dict) -> dict:
    tree = ctx["tree"]
    leaves = ctx["leaves"]
    get_attr = ctx["get_attr"]

    pdb_baseurl = (ctx.get("pdb_baseurl") or "").strip()
    pdb_map: Dict[str, str] = ctx.get("pdb_map") or {}
    epitopes: list = ctx.get("epitopes") or []
    meta = (ctx.get("data") or {}).get("meta", {}) or {}
    genome_annotations: dict = meta.get("genome_annotations", {}) or {}

    # Env-configurable intro params (ctx takes precedence)
    focal_country = ctx.get("focal_country") or os.getenv("ITOL_FOCAL_COUNTRY", "UAE").strip() or "UAE"
    min_conf_raw = ctx.get("min_conf")
    try:
        min_conf = float(min_conf_raw) if min_conf_raw is not None else float(
            os.getenv("ITOL_INTRO_MIN_CONF", "0.8")
        )
    except Exception:
        min_conf = 0.8

    has_ha_annotation = "HA" in genome_annotations

    # Ensure baseurl ends with /
    if pdb_baseurl and not pdb_baseurl.endswith("/"):
        pdb_baseurl += "/"

    # Build parent & node lookup
    parent_by_name: Dict[str, str] = {}
    node_by_name: Dict[str, dict] = {}
    for n, p in _walk(tree, None):
        name = n.get("name")
        if name:
            node_by_name[name] = n
            pname = p.get("name") if p else None
            if pname:
                parent_by_name[name] = pname

    lines = ["POPUP_INFO", "SEPARATOR TAB", "DATA"]

    for leaf in leaves:
        leaf_id = leaf["name"]

        region   = get_attr(leaf, "region",   "NA")
        date     = get_attr(leaf, "date",     "NA")
        country  = get_attr(leaf, "country",  "NA")
        division = get_attr(leaf, "division", "NA")
        clade    = get_attr(leaf, "clade",    "NA")
        num_date = get_attr(leaf, "num_date", "NA")

        # Confidence
        country_conf = _get_conf_map(leaf, "country")
        raw_conf = country_conf.get(focal_country)
        focal_conf_val: Optional[float]
        if raw_conf is None:
            focal_conf_val = None
        else:
            try:
                focal_conf_val = float(raw_conf)
            except (TypeError, ValueError):
                focal_conf_val = None
        focal_conf_str = f"{focal_conf_val:.3f}" if focal_conf_val is not None else "NA"

        # Introduction logic
        parent_name = parent_by_name.get(leaf_id)
        parent_node = node_by_name.get(parent_name) if parent_name else None
        parent_country = _get_value(parent_node, "country", "") if parent_node else ""

        is_intro = (
            country == focal_country
            and parent_country != focal_country
            and focal_conf_val is not None
            and focal_conf_val >= min_conf
        )

        # Mutations
        nuc_muts, aa_muts = _extract_mutations(leaf)
        nuc_count = len(nuc_muts)
        aa_count  = len(aa_muts)

        # Epitope/annotation mapping
        epitope_hits    = _map_to_epitopes(aa_muts, epitopes)
        annotation_hits = _map_to_annotations(aa_muts, genome_annotations)

        # Structure link
        pdb_file = pdb_map.get(leaf_id, "")
        pdb_url  = (pdb_baseurl + quote(pdb_file)) if (pdb_baseurl and pdb_file) else ""

        structure_html = (
            f"<p><b>Structure (PDB):</b> <a href='{escape(pdb_url)}' target='_blank'>Download PDB</a></p>"
            "<p><i>Open in PyMOL:</i> File &rarr; Open&hellip; (select the downloaded .pdb)</p>"
            if pdb_url
            else "<p><b>Structure (PDB):</b> not available for this sample.</p>"
        )

        intro_html = (
            "<h2>Introduction inference</h2>"
            "<table>"
            f"<tr><th>Focal country</th><td>{escape(str(focal_country))}</td></tr>"
            f"<tr><th>P(focal country)</th><td>{escape(focal_conf_str)}</td></tr>"
            f"<tr><th>Min. confidence</th><td>{escape(str(min_conf))}</td></tr>"
            f"<tr><th>Parent country</th><td>{escape(parent_country or 'NA')}</td></tr>"
            f"<tr><th>Is introduction?</th><td><b>{'YES' if is_intro else 'no'}</b></td></tr>"
            "</table>"
        )

        mut_html = (
            "<h2>Mutations (branch-specific)</h2>"
            "<table>"
            f"<tr><th>Nuc mutations ({nuc_count})</th><td>{escape(_fmt_list(nuc_muts))}</td></tr>"
            f"<tr><th>AA mutations ({aa_count})</th><td>{escape(_fmt_list(aa_muts))}</td></tr>"
            "</table>"
        )

        # Epitope / annotation mapping block
        if epitopes:
            ep_block = (
                "<h2>Epitope mapping (from TSV)</h2>"
                f"<p>{escape(_fmt_list(epitope_hits) if epitope_hits else 'No epitope region hits')}</p>"
            )
        elif has_ha_annotation:
            ep_block = (
                "<h2>Epitope / annotation mapping (JSON-only)</h2>"
                "<p><b>Note:</b> This auspice.json does not contain explicit epitope definitions. "
                "Using <code>meta.genome_annotations</code> feature mapping instead.</p>"
                f"<p><b>Annotation hits:</b> {escape(_fmt_list(annotation_hits) if annotation_hits else 'NA')}</p>"
            )
        else:
            ep_block = (
                "<h2>Epitope / annotation mapping</h2>"
                "<p><b>Unavailable:</b> No epitope definitions or genome_annotations found.</p>"
            )

        title = f"Sample: {leaf_id}"
        html = (
            "<div class='tPop'>"
            f"<h1>{escape(leaf_id)}</h1>"
            "<h2>Metadata</h2>"
            "<table>"
            f"<tr><th>Region</th><td>{escape(str(region))}</td></tr>"
            f"<tr><th>Date</th><td>{escape(str(date))}</td></tr>"
            f"<tr><th>Numeric date</th><td>{escape(str(num_date))}</td></tr>"
            f"<tr><th>Country</th><td>{escape(str(country))}</td></tr>"
            f"<tr><th>Division</th><td>{escape(str(division))}</td></tr>"
            f"<tr><th>Clade</th><td>{escape(str(clade))}</td></tr>"
            "</table>"
            f"{intro_html}"
            f"{mut_html}"
            f"{ep_block}"
            f"{structure_html}"
            "</div>"
        )

        lines.append(f"{leaf_id}\t{title}\t{html}")

    return {"dataset_popup_info_pymol.txt": "\n".join(lines) + "\n"}
