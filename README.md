# Augur2iToL — Nextstrain → Interactive Tree of Life Pipeline

> **Bioinformatics course project · Influenza B/Victoria HA phylogenetic analysis**

---

## Project Purpose

**Augur2iToL** is an automated pipeline that converts phylogenetic analysis outputs produced
by [Augur/Nextstrain](https://nextstrain.org/) (`auspice.json` format) into annotation
datasets for the [Interactive Tree of Life (iTOL)](https://itol.embl.de/) visualisation
platform.

### Scientific context

The project analyses Influenza B/Victoria Haemagglutinin (HA) sequences sampled in the
United Arab Emirates (UAE) alongside global sequences.  Key scientific questions:

1. **How many independent introductions** of Flu B/Victoria have entered UAE?
2. **Which clades/lineages** dominate local circulation?
3. **Where on the HA protein** do branch-specific mutations fall?  Do they land in known
   antigenic / epitope regions?
4. **Can PDB structural data** be linked from the phylogenetic viewer to enable 3-D
   mutation inspection in PyMOL?

---

## Work Done So Far

### Features implemented

| Feature | Status | Output file |
|---------|--------|-------------|
| Leaf labels dataset | Done | `dataset_labels.txt` |
| Introduction inference (country transitions + confidence) | Done | `dataset_introductions_<country>.txt` |
| Rich HTML popup (metadata + mutations + epitope hits + PDB link) | Done | `dataset_popup_info_pymol.txt` |
| Mutation count heatmap (branch-specific nuc + AA counts) | Done | `dataset_mutation_count_heatmap.txt` |
| Colour strips for region / country / clade / division | Done | `dataset_strip_<attr>.txt` |
| Epitope region mapping from TSV | Done | shown in popup |
| Genome annotation mapping (JSON-only fallback) | Done | shown in popup |
| iTOL batch upload helper | Done | `scripts/upload_itol.py` |

### Datasets / data files

| File | Description |
|------|-------------|
| `Example/auspice.json` | Minimal but fully functional Augur/Nextstrain phylogenetic JSON (Flu B HA, UAE focus).  Replace with the full dataset for production runs. |
| `data/epitopes_flu_b_ha.tsv` | Influenza B HA antigenic site definitions (sites I-V + receptor binding domain) with amino-acid coordinate ranges and display colours. |

---

## Repository Structure

```
bioinfo_/
|-- README.md                         <- This file; project summary & documentation
|
|-- Example/
|   `-- auspice.json                  <- Example Augur/Nextstrain output (Flu B HA, UAE)
|
|-- data/
|   `-- epitopes_flu_b_ha.tsv         <- Flu B HA antigenic site coordinates (TSV with header)
|
|-- scripts/
|   |-- itol_build.py                 <- Main pipeline: loads JSON, runs plugins, writes datasets
|   `-- upload_itol.py                <- Uploads dataset_*.txt files to iTOL via batch API
|
|-- itol_plugins/
|   |-- labels.py                     <- DATASET_TEXT: leaf tip labels
|   |-- introductions_country.py      <- DATASET_COLORSTRIP: country introduction events
|   |-- popup_pymol_links.py          <- POPUP_INFO: rich per-sample HTML popup
|   |-- mutation_summary.py           <- DATASET_HEATMAP: branch mutation counts
|   `-- attributes_strips.py          <- DATASET_COLORSTRIP x4: region/country/clade/division
|
|-- tests/
|   `-- test_plugins.py               <- 25 unit tests covering all plugins and pipeline helpers
|
`-- out/
    `-- itol/                         <- (git-ignored) Generated dataset_*.txt files land here
```

---

## Quick Start

### 1. Generate iTOL datasets

```bash
python scripts/itol_build.py \
  --auspice Example/auspice.json \
  --plugins labels introductions_country popup_pymol_links mutation_summary attributes_strips \
  --epitope-tsv data/epitopes_flu_b_ha.tsv \
  --out out/itol
```

### 2. Upload to iTOL

```bash
export ITOL_API_KEY="your_api_key_here"
export ITOL_TREE_ID="your_tree_id_here"
python scripts/upload_itol.py --dir out/itol
```

### 3. Run tests

```bash
python tests/test_plugins.py
```

### Environment variables (optional overrides)

| Variable | Default | Purpose |
|----------|---------|---------|
| `ITOL_FOCAL_COUNTRY` | `UAE` | Country label to track introductions into |
| `ITOL_INTRO_MIN_CONF` | `0.8` | Minimum introduction confidence threshold |
| `ITOL_PDB_BASEURL` | (empty) | Base URL for PDB structure downloads in popups |
| `ITOL_VIEWER_URL` | (empty) | URL of 3-D structure viewer page |
| `ITOL_API_KEY` | (required for upload) | iTOL API key |
| `ITOL_TREE_ID` | (required for upload) | iTOL tree ID to attach datasets to |

---

## Plugin Architecture

Every file in `itol_plugins/` must export exactly one function:

```python
def generate(ctx: dict) -> dict:
    """Return {filename: content_string}."""
```

The `ctx` dictionary passed by `itol_build.py` contains:

| Key | Type | Description |
|-----|------|-------------|
| `data` | dict | Full parsed `auspice.json` object |
| `tree` / `tree_root` | dict | Root node of the phylogenetic tree |
| `meta` | dict | `data["meta"]` shortcut |
| `leaves` | list | All tip/leaf nodes |
| `internals` | list | All internal (ancestor) nodes |
| `all_nodes` | list | Leaves + internals |
| `parent_map` | dict | `node_name -> parent_name` |
| `focal_country` | str | Country label for introduction analysis |
| `focal_abbr` | str | Short abbreviation of focal country |
| `min_conf` | float | Minimum confidence threshold |
| `pdb_baseurl` | str | Base URL for PDB files |
| `pdb_map` | dict | `node_name -> pdb_filename` |
| `viewer_url` | str | Viewer page URL |
| `epitopes` | list | Rows from the epitope TSV |
| `genome_annotations` | dict | `meta.genome_annotations` |
| `get_attr` | callable | `get_attr(node, key, default='')` helper |

---

## Professor Requirements Recap

The following tasks were originally requested for this project:

| # | Requirement | Status |
|---|-------------|--------|
| i | Convert Augur `auspice.json` to iTOL-compatible annotation files | Done |
| ii | Label leaf nodes with sample identifiers | Done (`labels.py`) |
| iii | Identify and visualise introduction events into UAE | Done (`introductions_country.py`) |
| iv | Display metadata per node (region, date, country, division, clade) | Done (popup) |
| v | Show branch-specific nucleotide and amino-acid mutations | Done (popup + heatmap) |
| vi | Map mutations to epitope / antigenic regions | Done (from TSV; JSON-only fallback) |
| vii | Link PDB structure files for 3-D inspection in PyMOL | Done (popup, active when ITOL_PDB_BASEURL is set) |
| viii | Generate colour strips for phylogenetic attributes | Done (`attributes_strips.py`) |

---

## Unpublished / In-Progress Features

The following features are planned but **not yet implemented**:

### Tree pruning / collapsing
`scripts/prune_auspice.py` — Planned script to:
- Read `auspice.json`
- Retain only leaves where `node_attrs.country.value == focal_country`
- Prune empty internal nodes
- Write a pruned `out/pruned_<country>_auspice.json`

Use case: generate a clean UAE-only tree for iTOL before uploading.

### Netlify 3-D structure viewer
A static `viewer.html` page hosted on Netlify that accepts `?pdb=<url>` as a query
parameter and renders the PDB file in-browser using NGL Viewer or Mol*.  The popup
already includes "Open 3D viewer" links; the viewer page is not yet built.

### GitHub Releases for PDB files
PDB structure files for representative UAE sequences are intended to be attached to a
GitHub Release (`v0.1-demo`).  The `ITOL_PDB_BASEURL` variable would point to the
GitHub Releases raw asset URL.

### Extended epitope annotation
Currently only uses `meta.genome_annotations` (HA CDS only) when no epitope TSV is
supplied.  Future work: auto-download published Flu B HA antigenic site coordinates
from a public database (e.g., BioPortal, FluDB) if no TSV is provided.

---

## Notes on Epitope Mapping

The example `auspice.json` (and the real dataset) contains only a single
`genome_annotations` entry for the HA CDS (`start=34, end=1710`).  No per-epitope
coordinate ranges are embedded in the JSON.

Epitope mapping therefore works as follows:
- **When `--epitope-tsv` is provided**: mutations are compared against named TSV ranges;
  hits are shown in the popup under "Epitope mapping (from TSV)".
- **When no TSV is provided**: the popup displays a note under
  "Epitope / annotation mapping (JSON-only)" explaining the limitation and reporting
  which CDS annotations are hit (e.g., `HA (CDS)`).

---

*Augur2iToL pipeline — Bioinformatics course project*
