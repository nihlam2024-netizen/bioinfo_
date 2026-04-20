# Bioinfo — Augur2iTOL Pipeline

A pipeline that parses **Auspice v2 JSON** phylogenetic tree data and generates
**iTOL**-compatible datasets with rich annotations:

- Introduction events: detect virus introductions into a focal country
  using inferred country confidence (configurable threshold, default 0.8)
- Mutations: extract nucleotide and amino-acid mutations per branch,
  map them to genome annotations and epitope regions
- Colour strips: country, region, clade, host, severity visualisations
- Rich popups: all metadata + mutations + epitope hits + 3D structure links
- Prune/collapse: filter tree to a focal country for focused analysis
- 3D viewer: 3Dmol.js static viewer deployable on Netlify / GitHub Pages

---

## Requirements

Python 3.8+ -- no external dependencies (standard library only).

Optional (for tests):
    pip install pytest

---

## Quick Start -- UAE Demo

### 1. Place your Auspice JSON

    cp /path/to/your/auspice.json Example/auspice.json

See `Example/README.md` for instructions on obtaining an Auspice JSON.

### 2. Build all iTOL datasets

    python scripts/itol_build.py \
      --auspice Example/auspice.json \
      --plugins labels introductions_country popup_pymol_links mutation_summary attributes_strips tree_colors_region \
      --focal-country "United Arab Emirates" \
      --focal-abbr UAE \
      --min-conf 0.8 \
      --epitope-tsv data/epitopes_flu_b_ha.tsv \
      --out out/itol

### 3. Prune to UAE-only tree

    python scripts/prune_auspice.py \
      --auspice Example/auspice.json \
      --keep-attr country \
      --keep-value "United Arab Emirates" \
      --out out/pruned_uae_auspice.json

    python scripts/itol_build.py \
      --auspice out/pruned_uae_auspice.json \
      --plugins labels popup_pymol_links mutation_summary \
      --focal-country "United Arab Emirates" \
      --focal-abbr UAE \
      --out out/itol_uae

### 4. Validate datasets

    python tests/validate_datasets.py out/itol/

### 5. Upload to iTOL

Upload the `out/itol/*.txt` files via the iTOL web interface at https://itol.embl.de/

---

## Plugins

| Plugin | Output file(s) | Description |
|---|---|---|
| labels | dataset_labels.txt | Leaf name list |
| introductions_country | dataset_introductions_UAE.txt | Introduction events colourstrip |
| popup_pymol_links | dataset_popup_info_pymol.txt | Rich popup: metadata, mutations, epitopes, PDB links |
| mutation_summary | dataset_mutation_counts.txt | Nuc + AA mutation count heatmap |
| attributes_strips | dataset_*_strip.txt | Country / region / clade / host / severity strips |
| tree_colors_region | dataset_region_colors.txt | Region colour strip |

---

## CLI Reference

### itol_build.py flags

  --auspice          (required) Path to Auspice v2 JSON
  --plugins          Space-separated plugin names (default: labels popup_pymol_links)
  --focal-country    Country name for intro detection (default: United Arab Emirates)
  --focal-abbr       Abbreviation for output file names (default: UAE)
  --min-conf         Confidence threshold for introductions (default: 0.8)
  --pdb-baseurl      Base URL for PDB files (e.g. GitHub Release)
  --viewer-url       URL of 3D viewer page (e.g. Netlify deployment)
  --epitope-tsv      Path to TSV file with epitope definitions
  --out              Output directory (default: out/itol)

### prune_auspice.py flags

  --auspice          (required) Path to Auspice v2 JSON
  --keep-attr        Node attribute to filter on (default: country)
  --keep-value       (required) Value(s) to keep (space-separated)
  --out              (required) Output path for pruned JSON

---

## Epitope Mapping

The Auspice JSON format does not embed immunological epitope definitions.
This pipeline uses two complementary mechanisms:

1. Genome annotation mapping (from JSON):
   AA mutations are automatically mapped to CDS/gene regions using
   meta.genome_annotations from the JSON.

2. External epitope TSV (--epitope-tsv):
   A tab-separated file with columns gene, epitope, aa_start, aa_end.
   A bundled default for Influenza B HA is at data/epitopes_flu_b_ha.tsv.

Custom epitope table format:
    gene    epitope   aa_start  aa_end  source  notes
    HA      MySite    100       120     Ref     Description

---

## 3D Structure Viewer

viewer.html is a self-contained static page using 3Dmol.js.

### Deploy on Netlify (free)
1. Go to netlify.com -> Add new site -> Deploy manually
2. Drag viewer.html into the deploy box
3. Note your Netlify URL, e.g. https://bioinfo-viewer.netlify.app
4. Pass it as --viewer-url when building datasets

### Usage
  https://your-site.netlify.app/viewer.html?pdb=<PDB_FILE_URL>
  https://your-site.netlify.app/viewer.html?id=6XM4

---

## Project Structure

    .
    ├── scripts/
    │   ├── itol_build.py          Main build script
    │   └── prune_auspice.py       Prune/collapse tree by attribute
    ├── itol_plugins/
    │   ├── __init__.py
    │   ├── labels.py
    │   ├── introductions_country.py   Introduction event detection
    │   ├── popup_pymol_links.py       Rich popup with mutations and epitopes
    │   ├── mutation_summary.py        Mutation count heatmap
    │   ├── attributes_strips.py       Attribute colour strips
    │   └── tree_colors_region.py      Region colour strip
    ├── data/
    │   └── epitopes_flu_b_ha.tsv  Flu B HA epitope definitions (literature)
    ├── viewer.html                3Dmol.js structure viewer (deploy on Netlify)
    ├── tests/
    │   ├── validate_datasets.py   iTOL dataset format validator
    │   └── test_plugins.py        Plugin unit tests
    ├── docs/
    │   ├── status.md              Current progress tracker
    │   └── plan.md                Delivery plan
    ├── Example/
    │   └── README.md
    └── requirements.txt

---

## Running Tests

    # Unit tests (no auspice.json needed)
    python -m pytest tests/test_plugins.py -v

    # Dataset format validation (after building)
    python tests/validate_datasets.py out/itol/

---

## Introduction Detection Algorithm

A node is flagged as an introduction event into the focal country when:
1. node_attrs.country.value == focal_country
2. node_attrs.country.confidence[focal_country] >= min_conf (default 0.8)
3. Parent node's country.value != focal_country

Applies to both leaf nodes (sampled sequences) and internal nodes
(inferred ancestral states). Marked in iTOL with a red colour strip and
labelled with the inferred origin country and confidence score.
