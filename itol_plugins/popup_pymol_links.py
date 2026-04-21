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
  A note is shown in the popup when no epitope definitions are present in the
  auspice.json, making the limitation explicit and transparent.

iTOL POPUP_INFO format (tab-separated):
  node_name <TAB> popup_title <TAB> popup_html_content
"""
from html import escape
from urllib.parse import quote


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


def _tr(label, value):
    """Return an HTML table row with escaped content."""
    return f"<tr><th>{escape(str(label))}</th><td>{escape(str(value))}</td></tr>"


def _tr_raw(label, value_html):
    """Return an HTML table row where value is already safe HTML."""
    return f"<tr><th>{escape(str(label))}</th><td>{value_html}</td></tr>"


def _fmt_mut_list(muts, max_items=25):
    """Format a mutation list, truncating if very long."""
    if not muts:
        return "none"
    items = [str(m) for m in muts]
    if len(items) <= max_items:
        return escape(", ".join(items))
    shown = escape(", ".join(items[:max_items]))
    return f"{shown} <i>(+{len(items) - max_items} more)</i>"


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

        # ---- Build HTML content (structured tables) ----

        # Section 1: Metadata table
        meta_rows = [_tr("Country", country or "NA")]
        if focal_conf is not None:
            meta_rows.append(_tr(f"P({focal_abbr})", f"{focal_conf:.3f}"))
        if region:
            meta_rows.append(_tr("Region", region))
        if division:
            meta_rows.append(_tr("Division", division))
        if date_display:
            meta_rows.append(_tr("Date", date_display))
        if clade:
            meta_rows.append(_tr("Clade", clade))
        if host:
            meta_rows.append(_tr("Host", host))
        if age:
            meta_rows.append(_tr("Age", age))
        if severity:
            meta_rows.append(_tr("Severity", severity))
        if ari:
            meta_rows.append(_tr("ARI/SARI", ari))
        if resistance:
            meta_rows.append(_tr("Antiviral resistance", resistance))
        meta_html = (
            "<h2>Metadata</h2>"
            "<table style='border-collapse:collapse'>"
            + "".join(meta_rows)
            + "</table>"
        )

        # Section 2: Introduction inference table
        if is_intro:
            intro_status_html = (
                "<b style='color:#e41a1c'>&#8658; YES — INTRODUCTION to "
                f"{escape(focal_abbr)}</b>"
            )
        elif country == focal_country:
            intro_status_html = f"Resident {escape(focal_abbr)}"
        else:
            intro_status_html = "No"
        intro_rows = [
            _tr("Focal country", focal_country),
            _tr_raw("Is introduction?", intro_status_html),
            _tr("P(focal)", f"{focal_conf:.3f}" if focal_conf is not None else "NA"),
            _tr("Threshold", str(min_conf)),
            _tr("Parent country", parent_country or "NA"),
        ]
        intro_html = (
            "<h2>Introduction inference</h2>"
            "<table style='border-collapse:collapse'>"
            + "".join(intro_rows)
            + "</table>"
        )

        # Section 3: Mutations table
        aa_rows = []
        for gene, muts in aa_muts.items():
            if muts:
                aa_rows.append(
                    _tr_raw(f"AA {escape(gene)} ({len(muts)})", _fmt_mut_list(muts))
                )
        nuc_preview_html = _fmt_mut_list(nuc_muts) if nuc_muts else "none"
        mut_rows = [
            _tr("Nuc mutation count", nuc_count),
            _tr("AA mutation count", aa_count),
            _tr_raw(f"Nuc mutations ({nuc_count})", nuc_preview_html),
        ] + aa_rows
        mut_html = (
            "<h2>Branch mutations</h2>"
            "<table style='border-collapse:collapse'>"
            + "".join(mut_rows)
            + "</table>"
        )

        # Section 4: Epitope / annotation mapping
        if annotation_hits:
            ann_items = "".join(
                f"<li>{escape(h)}</li>" for h in annotation_hits
            )
            ann_html = (
                "<h2>Genomic / epitope annotation</h2>"
                f"<ul>{ann_items}</ul>"
            )
        elif epitopes:
            ann_html = (
                "<h2>Genomic / epitope annotation</h2>"
                "<p><i>No epitope hits for mutations on this branch.</i></p>"
            )
        elif genome_annotations:
            ann_html = (
                "<h2>Epitope / annotation mapping</h2>"
                "<p><b>Note:</b> Epitope definitions are not present in this "
                "auspice.json; only <code>genome_annotations</code> gene spans "
                "are available (HA CDS). Mutations are reported per gene above. "
                "Supply <code>--epitope-tsv</code> for full epitope-level "
                "mapping.</p>"
            )
        else:
            ann_html = (
                "<h2>Epitope / annotation mapping</h2>"
                "<p><i>No genome_annotations or epitope definitions found in "
                "this auspice.json.</i></p>"
            )

        # Section 5: Structure links
        struct_parts = []
        if pdb_baseurl:
            pdb_fname = f"{name}.pdb"
            pdb_url = f"{pdb_baseurl}/{pdb_fname}"
            struct_parts.append(
                f"<a href='{escape(pdb_url)}' target='_blank'>Download PDB</a>"
            )
            if viewer_url:
                viewer_link = f"{viewer_url}?pdb={quote(pdb_url, safe='')}"
                struct_parts.append(
                    f"<a href='{escape(viewer_link)}' target='_blank'>"
                    "Open 3D Viewer</a>"
                )
        struct_html = (
            (
                "<h2>Structure</h2><p>"
                + " &nbsp;|&nbsp; ".join(struct_parts)
                + "</p>"
            )
            if struct_parts
            else "<h2>Structure</h2><p><i>Not available for this sample.</i></p>"
        )

        popup_html = (
            f"<div class='tPop'>"
            f"<h1>{escape(name)}</h1>"
            f"{meta_html}"
            f"{intro_html}"
            f"{mut_html}"
            f"{ann_html}"
            f"{struct_html}"
            f"</div>"
        )

        title = f"{name} ({country or 'NA'})"
        lines.append(f"{name}\t{title}\t{popup_html}")

    return {"dataset_popup_info_pymol.txt": "\n".join(lines) + "\n"}
