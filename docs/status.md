# Project Status — Augur2iToL (as of Monday 20 Apr 2026)

This file is the "second brain" for the Thursday presentation.  
Update the emoji badge when you finish each item and re-push.

---

## Legend
| Badge | Meaning |
|-------|---------|
| ✅ | Done and verified |
| 🟡 | Partially done — needs verification / upload |
| ❌ | Not started |
| 🔶 | Blocked / depends on data or decision |

---

## A. Foundation

| Item | Status | Notes |
|------|--------|-------|
| Official repo created & pushed (`nihlamadala/augur2itol`) | ✅ | Code on `origin/main` |
| iTOL API upload works | ✅ | Confirmed working |
| Auspice JSON inspected — country/region/confidence fields verified | ✅ | `node_attrs.country.confidence`, `branch_attrs.mutations` confirmed present |
| GitHub Releases approach decided (host PDBs as release assets) | 🟡 | Decision made; tag/release not yet created |

---

## B. Professor Requirements

### (i) + (ii) Introductions into focal country (conf ≥ 0.8)

| Sub-task | Status | Notes |
|----------|--------|-------|
| JSON supports it (`node_attrs.country.confidence`) | ✅ | Field verified |
| Plugin `itol_plugins/introductions_country.py` written | ✅ | File exists, 3002 bytes |
| Build produces `out/itol/dataset_introductions_UAE.txt` | ✅ | 21 intro nodes detected |
| Dataset uploaded to iTOL and visible in UI | 🟡 | **Tonight — must verify** |
| Popup includes focal-country confidence + parent country + is_intro flag | ❌ | **Tonight — add to popup plugin** |

### (iii) Collapse / prune non-UAE leaves

| Sub-task | Status | Notes |
|----------|--------|-------|
| "Prune by country" script / flag | ❌ | **Tuesday** |
| True iTOL collapse dataset | ❌ | **Tuesday (stretch)** — if prune is done first |

### (iv) Mutation info + Epitope mapping

| Sub-task | Status | Notes |
|----------|--------|-------|
| `branch_attrs.mutations` confirmed in JSON | ✅ | Field verified |
| AA / Nuc mutation list shown in popup | ❌ | **Tuesday** |
| Mutation count heatmap strip (optional) | ❌ | **Tuesday (stretch)** |
| Epitope definitions located in JSON | 🔶 | Run meta scan (see `docs/plan.md` §0) |
| Mutations mapped to epitope regions in popup | ❌ | **Tuesday–Wednesday** (depends on epitope discovery) |

### (v) 3D Structure viewer in popup

| Sub-task | Status | Notes |
|----------|--------|-------|
| Subset PDB files selected (~10–30 nodes) | ❌ | **Wednesday** |
| GitHub Release `v0.1-demo` created with PDB assets | ❌ | **Wednesday** |
| `viewer.html` (3Dmol.js) static page built | ❌ | **Wednesday** |
| Netlify deployment (drag-and-drop) | ❌ | **Wednesday** |
| Popup "Open 3D viewer" link working end-to-end | ❌ | **Wednesday** |

### (vi) Country / metadata shown in popup

| Sub-task | Status | Notes |
|----------|--------|-------|
| Country shown in popup | ✅ | Already implemented |
| Severity / age / derived metrics | 🔶 | Depends on fields in JSON; if absent, document as "not in source data" |

---

## C. Deliverable Polish

| Item | Status | Notes |
|------|--------|-------|
| `docs/status.md` (this file) | ✅ | Created tonight |
| `docs/plan.md` (delivery schedule) | ✅ | Created tonight |
| README Quickstart (one-command reproduce) | ❌ | **Thursday morning** |
| Final iTOL public link | ❌ | **Thursday morning** |
| 5-slide presentation outline | ❌ | **Thursday morning** |

---

## D. Current iTOL link

> _Paste your current iTOL tree URL here after each upload._

```
iTOL link: (not yet recorded — paste after tonight's upload)
```

---

## E. "Golden command" — always keep this working

```bash
# From /mnt/c/Users/ASUS/Desktop/Augur2iToL
python scripts/itol_build.py \
  --auspice Example/auspice.json \
  --plugins labels popup_pymol_links introductions_country

python scripts/upload_itol.py
```

---

_Last updated: Mon 20 Apr 2026_
