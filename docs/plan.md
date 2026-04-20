# Implementation Plan

## Phase 1 — Core Pipeline (2026-04-20) ✅

- [x] `scripts/itol_build.py` — plugin-based build system with full CLI flags
- [x] `itol_plugins/introductions_country.py` — detect introduction events
- [x] `itol_plugins/popup_pymol_links.py` — rich popup with mutations, epitopes, PDB
- [x] `itol_plugins/mutation_summary.py` — mutation count heatmap
- [x] `itol_plugins/attributes_strips.py` — attribute colour strips
- [x] `itol_plugins/tree_colors_region.py` — region colour strip
- [x] `scripts/prune_auspice.py` — prune/collapse tree by attribute
- [x] `data/epitopes_flu_b_ha.tsv` — Flu B HA epitope definitions
- [x] `viewer.html` — 3Dmol.js structure viewer
- [x] `tests/validate_datasets.py` — dataset format validator
- [x] `tests/test_plugins.py` — plugin unit tests
- [x] `README.md` — full workflow and CLI documentation
- [x] `docs/status.md` and `docs/plan.md`

## Phase 2 — Upload & Validate (2026-04-21)

- [ ] Place `auspice.json` in `Example/` folder
- [ ] Run full build:
  ```bash
  python scripts/itol_build.py \
    --auspice Example/auspice.json \
    --plugins labels introductions_country popup_pymol_links mutation_summary attributes_strips \
    --epitope-tsv data/epitopes_flu_b_ha.tsv \
    --out out/itol
  ```
- [ ] Run validation: `python tests/validate_datasets.py out/itol/`
- [ ] Upload datasets to iTOL and confirm each strip renders
- [ ] Confirm popup shows mutations + intro flag

## Phase 3 — 3D Structures & Hosting (2026-04-22)

- [ ] Create GitHub Release `v0.1-demo`
- [ ] Upload 10–30 representative PDB files as release assets
- [ ] Deploy `viewer.html` on Netlify:
  1. Go to [netlify.com](https://netlify.com) → Add new site → Deploy manually
  2. Drag `viewer.html` into the deploy box
  3. Note the Netlify URL
- [ ] Rebuild with `--pdb-baseurl` and `--viewer-url`:
  ```bash
  python scripts/itol_build.py \
    --auspice Example/auspice.json \
    --plugins labels introductions_country popup_pymol_links mutation_summary attributes_strips \
    --epitope-tsv data/epitopes_flu_b_ha.tsv \
    --pdb-baseurl "https://github.com/nihlamadala/augur2itol/releases/download/v0.1-demo" \
    --viewer-url "https://your-netlify-site.netlify.app/viewer.html" \
    --out out/itol
  ```
- [ ] Confirm "Download PDB" and "Open 3D Viewer" popup links work

## Phase 4 — Polish + Demo (2026-04-24)

- [ ] Run end-to-end from a clean terminal (clean `out/` first)
- [ ] Final README pass — "How to Reproduce" section
- [ ] Prepare demo narrative:
  1. Objective & pipeline overview
  2. Introduction detection (conf >= 0.8, UAE)
  3. UAE-focused tree (prune/collapse)
  4. Mutations + epitope mapping in popup
  5. 3D structure viewer demo

## UAE Demo Commands (Quick Reference)

```bash
# 1. Build all datasets
python scripts/itol_build.py \
  --auspice Example/auspice.json \
  --plugins labels introductions_country popup_pymol_links mutation_summary attributes_strips tree_colors_region \
  --focal-country "United Arab Emirates" \
  --focal-abbr UAE \
  --min-conf 0.8 \
  --epitope-tsv data/epitopes_flu_b_ha.tsv \
  --out out/itol

# 2. Prune to UAE-only tree
python scripts/prune_auspice.py \
  --auspice Example/auspice.json \
  --keep-attr country \
  --keep-value "United Arab Emirates" \
  --out out/pruned_uae_auspice.json

# 3. Build datasets for pruned UAE tree
python scripts/itol_build.py \
  --auspice out/pruned_uae_auspice.json \
  --plugins labels popup_pymol_links mutation_summary \
  --focal-country "United Arab Emirates" \
  --focal-abbr UAE \
  --out out/itol_uae

# 4. Validate all datasets
python tests/validate_datasets.py out/itol/

# 5. Run tests
python -m pytest tests/test_plugins.py -v
```
