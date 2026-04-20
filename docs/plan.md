# Delivery Plan — Augur2iToL (Mon 20 Apr → Thu 23 Apr 2026)

> **Objective**: Complete ≥ 50 % of all professor requirements tonight (Monday), and have a fully demo-ready presentation by Thursday.

---

## § 0  Run the epitope meta-scan right now (takes 2 minutes)

Before doing anything else, find out what epitope data, if any, is already in your JSON:

```bash
python - <<'PY'
import json
from pathlib import Path

j = json.loads(Path("Example/auspice.json").read_text(encoding="utf-8"))
meta = j.get("meta", {})
print("meta keys:", sorted(meta.keys()))

def find_epitope(obj, path="meta"):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if "epitope" in k.lower():
                found.append((p, type(v).__name__))
            found.extend(find_epitope(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:200]):
            found.extend(find_epitope(v, f"{path}[{i}]"))
    return found

hits = find_epitope(meta)
print("Epitope-like paths found:", hits[:50] if hits else "NONE")
PY
```

**Decision tree**

| Result | What to do |
|--------|-----------|
| Epitope paths found in JSON | Use those ranges to map mutations → epitope regions (see Tuesday §4b). |
| No epitope paths in JSON | Create `epitopes.tsv` with known H3N2/flu antigenic regions from literature; professor will see it as a companion input file — fully acceptable. |

---

## MONDAY NIGHT (today) — target ≥ 50 % done by midnight

> Everything below should take **3–4 hours** in total.

### Task 1 — Verify introductions dataset in iTOL (~30 min)
**Goal**: intro color-strip appears on the tree in iTOL.

- [ ] Run build (confirms existing work is intact):
  ```bash
  python scripts/itol_build.py \
    --auspice Example/auspice.json \
    --plugins labels popup_pymol_links introductions_country
  ```
- [ ] Confirm file exists and has data rows:
  ```bash
  wc -l out/itol/dataset_introductions_UAE.txt
  head -n 25 out/itol/dataset_introductions_UAE.txt
  ```
- [ ] Upload to iTOL:
  ```bash
  python scripts/upload_itol.py
  ```
- [ ] Open iTOL in browser → enable "Introductions to UAE" dataset → screenshot.
- [ ] Paste the iTOL tree URL into `docs/status.md`.

---

### Task 2 — Fix header TAB formatting in introductions plugin (~20 min)
**Goal**: All iTOL header lines use `\t` (not spaces).

- [ ] Open `itol_plugins/introductions_country.py`.
- [ ] Find every `f"DATASET_LABEL   {label}"` / `f"COLOR   {color}"` pattern.
- [ ] Change each to use `\t` separator:
  ```python
  f"DATASET_LABEL\t{label}"
  f"COLOR\t#e41a1c"
  # etc.
  ```
- [ ] Verify with:
  ```bash
  python scripts/itol_build.py ...
  cat -A out/itol/dataset_introductions_UAE.txt | head -n 12
  # Should show ^I (tab) not spaces
  ```
- [ ] Re-upload after fixing.

---

### Task 3 — Add intro fields to popup plugin (~60–90 min)
**Goal**: Each node popup shows `P(UAE)`, `Is intro`, and `Parent country`.

In `itol_plugins/popup_pymol_links.py` (or wherever popups are built), for each leaf add three rows to the popup table:

```python
# --- introductions fields ---
country_conf = node.get("node_attrs", {}).get("country", {}).get("confidence", {})
focal_conf   = country_conf.get("United Arab Emirates", 0.0)
parent_ctry  = _get_parent_country(node, tree)   # helper — see below
is_intro     = "YES" if (focal_conf >= 0.8 and parent_ctry not in ("United Arab Emirates", None)) else "no"

popup_rows += [
    f"P(UAE)\t{focal_conf:.3f}",
    f"Intro to UAE\t{is_intro}",
    f"Parent country\t{parent_ctry or 'unknown'}",
]
```

Helper to get parent country (add near top of plugin file):

```python
def _get_parent_country(node, tree):
    """Return country value of direct parent node, or None if root."""
    node_name = node.get("name")
    for candidate in tree.get("tree", {}).get("children", []):
        result = _find_parent_country(candidate, node_name)
        if result is not None:
            return result
    return None

def _find_parent_country(subtree, target_name, parent_country=None):
    if subtree.get("name") == target_name:
        return parent_country
    for child in subtree.get("children", []):
        result = _find_parent_country(
            child, target_name,
            subtree.get("node_attrs", {}).get("country", {}).get("value")
        )
        if result is not None:
            return result
    return None
```

- [ ] Implement and rebuild.
- [ ] Open iTOL, click a node marked as intro → verify popup shows three new rows.
- [ ] Screenshot the popup.

---

### Task 4 — Commit, push, and update docs/status.md (~20 min)

- [ ] Update `docs/status.md` — mark completed items ✅.
- [ ] Run:
  ```bash
  git add itol_plugins/introductions_country.py \
          itol_plugins/popup_pymol_links.py \
          docs/status.md docs/plan.md
  git commit -m "feat: introductions validated in iTOL + popup intro fields"
  git push
  ```

---

## TUESDAY — Collapse/prune + Mutations

### Task 5 — Prune tree to UAE-only (~2 hrs)
- [ ] Add a script `scripts/prune_tree.py` (or flag to `itol_build.py`) that:
  - walks the Auspice tree
  - keeps only leaves where `node_attrs.country.value == "United Arab Emirates"`
  - writes `out/itol/dataset_prune_UAE_only.txt`  
    _Alternatively_: writes a pruned Newick and uploads as a second iTOL tree.
- [ ] Upload and verify in iTOL.

### Task 6 — Mutations in popup (~2–3 hrs)
- [ ] In popup plugin, parse `branch_attrs.mutations`:
  ```python
  muts = node.get("branch_attrs", {}).get("mutations", {})
  aa_muts  = muts.get("aa",  {})   # dict of gene → list of strings
  nuc_muts = muts.get("nuc", [])   # list of strings
  aa_str   = "; ".join(f"{g}: {','.join(v)}" for g,v in aa_muts.items()) or "none"
  nuc_str  = ", ".join(nuc_muts[:10]) or "none"  # cap at 10 for display
  mut_count = sum(len(v) for v in aa_muts.values()) + len(nuc_muts)
  popup_rows += [
      f"AA mutations\t{aa_str}",
      f"Nuc mutations\t{nuc_str}",
      f"Mutation count\t{mut_count}",
  ]
  ```
- [ ] Rebuild, re-upload, screenshot.

### Task 7 — Epitope mapping (~2–3 hrs, depends on § 0 result)
**If JSON has epitope data**:
- Map each mutation to its epitope region from the JSON ranges.
- Add `Epitope sites hit` row to popup.

**If JSON has no epitope data** (likely):
- Create `epitopes.tsv` in repo root with columns:
  `region_name | gene | aa_start | aa_end`
  Use standard H3 HA antigenic sites (Sa, Sb, Ca1, Ca2, Cb) from literature.
- Add `scripts/map_epitopes.py` that reads this file and reports which mutations fall in epitope regions.
- Add `Epitope sites hit` row to popup.

---

## WEDNESDAY — Structures + 3D viewer

### Task 8 — GitHub Release with PDB subset (~2 hrs)
- [ ] Select 10–30 representative leaves that have PDB files.
- [ ] Create GitHub Release `v0.1-demo` on `nihlamadala/augur2itol`.
- [ ] Upload PDB files as release assets.
- [ ] Confirm download URLs work:
  `https://github.com/nihlamadala/augur2itol/releases/download/v0.1-demo/<name>.pdb`
- [ ] Set `--pdb-baseurl` in build command to this URL prefix.

### Task 9 — Static 3D viewer (Netlify) (~2–3 hrs)
- [ ] Create `viewer/viewer.html`:
  ```html
  <!DOCTYPE html>
  <html>
  <head>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
  </head>
  <body>
  <div id="viewer" style="width:800px;height:600px;position:relative;"></div>
  <script>
    const params = new URLSearchParams(window.location.search);
    const pdbUrl = params.get("pdb");
    const viewer = $3Dmol.createViewer("viewer", {backgroundColor:"white"});
    fetch(pdbUrl).then(r => r.text()).then(data => {
      viewer.addModel(data, "pdb");
      viewer.setStyle({}, {cartoon:{color:"spectrum"}});
      viewer.zoomTo();
      viewer.render();
    });
  </script>
  </body>
  </html>
  ```
- [ ] Deploy `viewer/` folder to Netlify (drag-and-drop UI).
- [ ] Note your Netlify URL, e.g. `https://augur2itol-viewer.netlify.app`.
- [ ] In popup plugin, add: `f"3D viewer\t<a href='https://augur2itol-viewer.netlify.app/viewer.html?pdb={pdb_url}'>Open</a>"`
- [ ] Rebuild, re-upload, test link.

---

## THURSDAY MORNING — Polish + Rehearsal

### Task 10 — Clean-room final run (~1 hr)
- [ ] Open fresh terminal.
- [ ] Set `ITOL_APIKEY`.
- [ ] Run build + upload end-to-end.
- [ ] Verify all datasets visible in iTOL.
- [ ] Verify popup has: country, P(UAE), is_intro, parent_country, AA muts, Nuc muts, epitope hits, 3D viewer link.

### Task 11 — README Quickstart (~1 hr)
- [ ] Add section to `README.md`:
  ```markdown
  ## Quick Start
  1. `pip install -r requirements.txt`
  2. `export ITOL_APIKEY=<your key>`
  3. `python scripts/itol_build.py --auspice Example/auspice.json --plugins labels popup_pymol_links introductions_country`
  4. `python scripts/upload_itol.py`
  ```

### Task 12 — 5-slide deck (1–2 hrs)
| Slide | Content |
|-------|---------|
| 1 | Problem + objective |
| 2 | Pipeline diagram (Augur JSON → plugins → iTOL) |
| 3 | Intro detection demo (screenshot: tree + color strip + popup) |
| 4 | Mutations + epitope map (screenshot: popup with AA muts + epitope hits) |
| 5 | Structure viewer demo + what's next (severity, true collapse, full epitope coverage) |

---

## "No hiccups" rules

1. **Do NOT touch TREE_COLORS** — it already breaks. Leave it alone.
2. Every new feature is an **optional plugin** — default build must still work.
3. End every work session by running the golden command and verifying it still works.
4. End every day with:
   - working iTOL link (paste in `docs/status.md`)
   - `git commit + push`
5. If you get stuck on epitopes for > 45 minutes, use the `epitopes.tsv` fallback (§ Tuesday Task 7) — do not let it block mutations, which are higher priority.

---

## Priority order (if time is short)

1. ✅ Introductions dataset working in iTOL ← already generating
2. 🔴 Popup shows `P(UAE)` + `is_intro` + `parent_country` ← **tonight**
3. 🔴 AA/Nuc mutations in popup ← **Tuesday**
4. 🔴 Epitope mapping in popup ← **Tuesday–Wednesday**
5. 🟡 Prune/collapse tree ← **Tuesday** (can demo even without true collapse)
6. 🟡 3D structure viewer ← **Wednesday** (nice-to-have for prof)
7. 🟢 README + slides ← **Thursday morning**

---

_Last updated: Mon 20 Apr 2026_
