# Project Status

**Updated:** 2026-04-20

## Feature Status

| Feature | Status | Notes |
|---|---|---|
| Auspice JSON parsing | ✅ Done | `scripts/itol_build.py` reads Auspice v2 JSON |
| Introduction detection (conf >= threshold) | ✅ Done | `itol_plugins/introductions_country.py` |
| Rich popup (mutations, intros, epitopes, PDB links) | ✅ Done | `itol_plugins/popup_pymol_links.py` |
| Mutation count heatmap | ✅ Done | `itol_plugins/mutation_summary.py` |
| Attribute colour strips (country, region, clade) | ✅ Done | `itol_plugins/attributes_strips.py` |
| Region colour strip | ✅ Done | `itol_plugins/tree_colors_region.py` |
| Collapse/prune to focal country | ✅ Done | `scripts/prune_auspice.py` |
| Epitope mapping (genome_annotations + optional TSV) | ✅ Done | `data/epitopes_flu_b_ha.tsv` bundled; pass `--epitope-tsv` |
| 3D structure viewer (3Dmol.js) | ✅ Done | `viewer.html` — deploy on Netlify / GitHub Pages |
| Dataset validation tests | ✅ Done | `tests/validate_datasets.py` |
| Plugin unit tests | ✅ Done | `tests/test_plugins.py` |
| README with full workflow | ✅ Done | See root `README.md` |

## Active iTOL Tree

<!-- Fill in your iTOL tree URL after uploading -->
- **iTOL link:** _TBD — upload `out/itol/*.txt` via iTOL web UI_

## Known Limitations / Decisions

### Epitope definitions
The Auspice JSON for Influenza B Victoria HA does **not** embed immunological
epitope definitions. The pipeline handles this in two ways:

1. **Genome annotation mapping** — AA mutations are mapped to CDS regions from
   `meta.genome_annotations` (HA, nuc) automatically from the JSON.
2. **External epitope TSV** — `data/epitopes_flu_b_ha.tsv` provides literature-
   derived Flu B HA antigenic sites (Sa, Sb, Ca, Cb, Cc, RBS, stalk regions).
   Pass `--epitope-tsv data/epitopes_flu_b_ha.tsv` when building datasets.

This approach is honest and documented; the popup shows a note when epitope
definitions are not directly embedded in the JSON.

### TREE_COLORS clade style
The iTOL `TREE_COLORS` dataset was deferred — iTOL rejected it with
"Unknown clade style". `DATASET_COLORSTRIP` is used instead for all
colour-by-attribute visualisations.

### Clinical attributes (age, severity, ARI/SARI, resistance)
These fields are shown in popups **when present** in the Auspice JSON.
The Flu B dataset does not include them. The code is ready to display them
if a richer JSON is provided.
