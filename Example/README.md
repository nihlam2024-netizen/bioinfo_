# Example Directory

Place your `auspice.json` (Auspice v2 format, produced by Nextstrain/Augur) here.

## Getting an Auspice JSON

1. **From your local machine** — copy your existing `Example/auspice.json` into this folder.
2. **From Nextstrain** — download any public dataset:
   ```bash
   curl -L "https://nextstrain.org/charon/getDataset?prefix=flu/seasonal/h3n2/ha/2y" \
       -o Example/auspice.json
   ```
3. **From Augur** — run a nextstrain/augur workflow and copy the resulting `auspice/*.json` here.

## Required JSON Structure

The pipeline expects Auspice **v2** JSON with:
- `meta.genome_annotations` — gene/CDS coordinate map
- `tree` — phylogenetic tree with `node_attrs` and `branch_attrs`
- `node_attrs.country.value` — inferred country per node
- `node_attrs.country.confidence` — per-country probability map
- `branch_attrs.mutations` — branch-specific nuc and AA mutations

The Influenza B Victoria HA dataset used during development satisfies all requirements.
