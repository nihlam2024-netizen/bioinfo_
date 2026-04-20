"""
Plugin: popup_pymol_links — generate rich POPUP_INFO dataset for iTOL.

Each node popup includes:
  - Core metadata: country, region, division, date, clade, host
  - Clinical/epidemiological fields: age, severity, ARI/SARI, resistance
    (shown when present in the Auspice JSON; these fields may be absent)
  - Introduction info: P(focal_country), intro flag, parent country
  - Branch mutations: nucleotide (nuc) and amino-acid (per gene)
  - Genomic annotation hits: AA mutations mapped to genome_annotations
    regions and/or user-supplied epitope definitions
  - Structure links: "Download PDB" and "Open 3D Viewer" (when URLs are set)

Epitope mapping strategy:
  If --epitope-tsv is provided, AA mutations are checked against those regions.
  Regardless, mutations are mapped to genes listed in meta.genome_annotations.
  A note is shown in the popup when no epitope definitions are present.

iTOL POPUP_INFO format (tab-separated):
  node_name <TAB> popup_title <TAB> popup_html_content
"""


def _node_name(node):
    return node.get("name", "")


def _get_attr(node, key):
    """Retrieve node_attrs[key].value, returning '' if absent."""
    return node.get("node_attrs", {}).get(key, {}).get("value", "")


def _country_value(node):
    return _get_attr(node, "country")


def _confidence_for(node, country):
    return (
        node.get("node_attrs", {})
        .get("country", {})
        .get("confidence", {})
        .get(country, None)
    )


def _get_mutations(node):
    """Return (nuc_list, aa_dict) from branch_attrs.mutations."""
    branch = node.get("branch_attrs", {})
    muts = branch.get("mutations", {})
    nuc = list(muts.get("nuc", []))
    aa = {k: list(v) for k, v in muts.items() if k != "nuc"}
    return nuc, aa


def _map_to_annotations(aa_mutations, genome_annotations, epitopes):
    """Map AA mutations to genome annotation regions and epitope definitions.

    Returns a list of human-readable annotation/epitope hit strings.
    """
    hits = []

    for gene, muts in aa_mutations.items():
        if not muts:
            continue

        # Map to genome annotation gene span
        ann = genome_annotations.get(gene)
        if ann:
            start_nt = ann.get("start", 0)
            end_nt = ann.get("end", 0)
            gene_len_aa = max(1, (end_nt - start_nt) // 3)
            hits.append(
                f"Gene {gene}: {len(muts)} mutation(s) "
                f"(CDS nt {start_nt}-{end_nt}, ~{gene_len_aa} aa)"
            )

        # Map to epitope regions if available
        if gene in epitopes:
            for ep in epitopes[gene]:
                ep_hits = []
                for mut in muts:
                    try:
                        # Extract position number from mutation string, e.g. D225G -> 225
                        pos_str = "".join(c for c in mut[1:-1] if c.isdigit())
                        if not pos_str:
                            continue
                        pos = int(pos_str)
                        if ep["start"] <= pos <= ep["end"]:
                            ep_hits.append(mut)
                    except (ValueError, IndexError):
                        continue
                if ep_hits:
                    hits.append(
                        f"Epitope {ep['name']} ({gene} aa {ep['start']}-{ep['end']}): "
                        + ", ".join(ep_hits)
                    )

    return hits


def generate(ctx):
    focal_country = ctx["focal_country"]
    focal_abbr = ctx["focal_abbr"]
    min_conf = ctx["min_conf"]
    parent_map = ctx["parent_map"]
    pdb_baseurl = ctx["pdb_baseurl"]
    viewer_url = ctx["viewer_url"]
    genome_annotations = ctx["genome_annotations"]
    epitopes = ctx["epitopes"]
    all_nodes = ctx["all_nodes"]

    lines = [
        "POPUP_INFO",
        "SEPARATOR TAB",
        "DATA",
    ]

    for node in all_nodes:
        name = _node_name(node)
        if not name:
            continue

        # ---- Core metadata ----
        country = _get_attr(node, "country")
        region = _get_attr(node, "region")
        division = _get_attr(node, "division")
        clade = _get_attr(node, "clade_membership") or _get_attr(node, "clade")
        host = _get_attr(node, "host")

        # Date: prefer num_date (decimal year), fall back to date string
        num_date = _get_attr(node, "num_date")
        date_str = _get_attr(node, "date")
        if num_date:
            try:
                date_display = f"{float(num_date):.3f}"
            except (TypeError, ValueError):
                date_display = str(num_date)
        else:
            date_display = str(date_str) if date_str else ""

        # Clinical / epidemiological (may be absent)
        age = _get_attr(node, "age")
        severity = _get_attr(node, "severity")
        ari = (
            _get_attr(node, "ari")
            or _get_attr(node, "ARI")
            or _get_attr(node, "SARI")
            or _get_attr(node, "ari_sari")
        )
        resistance = _get_attr(node, "resistance") or _get_attr(
            node, "antiviral_resistance"
        )

        # ---- Introduction status ----
        parent = parent_map.get(name)
        parent_country = _country_value(parent) if parent else None
        focal_conf = _confidence_for(node, focal_country)
        is_intro = (
            country == focal_country
            and parent_country != focal_country
            and focal_conf is not None
            and focal_conf >= min_conf
        )

        # ---- Branch mutations ----
        nuc_muts, aa_muts = _get_mutations(node)
        nuc_count = len(nuc_muts)
        aa_count = sum(len(v) for v in aa_muts.values())

        # ---- Annotation / epitope hits ----
        annotation_hits = _map_to_annotations(aa_muts, genome_annotations, epitopes)

        # ---- Build HTML content ----
        parts = []

        parts.append(f"<b>{name}</b>")

        # Country + confidence
        if country:
            conf_str = (
                f" &nbsp; P({focal_abbr})={focal_conf:.3f}"
                if focal_conf is not None
                else ""
            )
            parts.append(f"Country: {country}{conf_str}")
        if region:
            parts.append(f"Region: {region}")
        if division:
            parts.append(f"Division: {division}")
        if date_display:
            parts.append(f"Date: {date_display}")
        if clade:
            parts.append(f"Clade: {clade}")
        if host:
            parts.append(f"Host: {host}")

        # Clinical fields (only shown when present in the JSON)
        if age:
            parts.append(f"Age: {age}")
        if severity:
            parts.append(f"Severity: {severity}")
        if ari:
            parts.append(f"ARI/SARI: {ari}")
        if resistance:
            parts.append(f"Antiviral resistance: {resistance}")

        # Introduction block
        if is_intro:
            parts.append(
                f"<b style='color:#e41a1c'>&#8658; INTRODUCTION to {focal_abbr}</b>"
            )
            parts.append(f"Origin (parent country): {parent_country or 'NA'}")
            parts.append(f"Introduction confidence: {focal_conf:.3f}")
        elif country == focal_country and focal_conf is not None:
            parts.append(
                f"Status: Resident {focal_abbr} (conf={focal_conf:.3f})"
            )

        # Mutation block
        parts.append("<b>Branch mutations:</b>")
        if nuc_count:
            preview = ", ".join(nuc_muts[:20])
            if nuc_count > 20:
                preview += f" ... (+{nuc_count - 20} more)"
            parts.append(f"Nuc ({nuc_count}): {preview}")
        if aa_count:
            for gene, muts in aa_muts.items():
                if muts:
                    parts.append(f"AA {gene} ({len(muts)}): {', '.join(muts)}")
        if not nuc_count and not aa_count:
            parts.append("None on this branch")

        # Annotation / epitope hits
        if annotation_hits:
            parts.append("<b>Genomic / epitope annotation:</b>")
            for h in annotation_hits:
                parts.append(f"&nbsp;&nbsp;{h}")
        elif not epitopes and genome_annotations:
            parts.append(
                "<i>Note: Epitope definitions not embedded in auspice.json; "
                "using genome_annotations gene mapping only. "
                "Supply --epitope-tsv for full epitope mapping.</i>"
            )

        # Structure links
        if pdb_baseurl:
            pdb_fname = f"{name}.pdb"
            pdb_url = f"{pdb_baseurl}/{pdb_fname}"
            parts.append(f"<a href='{pdb_url}' target='_blank'>Download PDB</a>")
            if viewer_url:
                from urllib.parse import quote
                viewer_link = f"{viewer_url}?pdb={quote(pdb_url, safe='')}"
                parts.append(
                    f"<a href='{viewer_link}' target='_blank'>Open 3D Viewer</a>"
                )

        popup_html = "<br/>".join(parts)
        title = f"{name} ({country or 'NA'})"
        lines.append(f"{name}\t{title}\t{popup_html}")

    return {"dataset_popup_info_pymol.txt": "\n".join(lines) + "\n"}
