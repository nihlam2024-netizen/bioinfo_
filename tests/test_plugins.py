"""
Unit tests for the Augur2iTOL plugin system.

Tests use minimal in-memory fixtures — no real auspice.json required.
Run with:
    python -m pytest tests/test_plugins.py -v
    # or directly:
    python tests/test_plugins.py
"""
import json
import os
import sys
import unittest
from pathlib import Path

# Ensure repo root is on the path
REPO_ROOT = str(Path(__file__).parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# ---------------------------------------------------------------------------
# Minimal Auspice-like fixture
# ---------------------------------------------------------------------------

LEAF_UAE = {
    "name": "LEAF_UAE_001",
    "node_attrs": {
        "country": {
            "value": "United Arab Emirates",
            "confidence": {"United Arab Emirates": 0.95, "France": 0.05},
        },
        "region": {"value": "Middle East"},
        "num_date": {"value": 2023.5},
        "clade_membership": {"value": "CladeA"},
        "host": {"value": "Human"},
    },
    "branch_attrs": {
        "mutations": {
            "nuc": ["A234T", "C987G"],
            "HA": ["D225G", "K189N"],
        }
    },
}

LEAF_FRANCE = {
    "name": "LEAF_FRANCE_001",
    "node_attrs": {
        "country": {
            "value": "France",
            "confidence": {"France": 0.98, "United Arab Emirates": 0.02},
        },
        "region": {"value": "Europe"},
        "num_date": {"value": 2023.3},
    },
    "branch_attrs": {
        "mutations": {
            "nuc": ["G100A"],
            "HA": ["N145K"],
        }
    },
}

PARENT_NODE = {
    "name": "NODE_ROOT",
    "node_attrs": {
        "country": {
            "value": "France",
            "confidence": {"France": 0.97, "United Arab Emirates": 0.03},
        },
        "region": {"value": "Europe"},
        "num_date": {"value": 2023.0},
    },
    "children": [LEAF_UAE, LEAF_FRANCE],
}


def make_ctx(focal="United Arab Emirates", min_conf=0.8, pdb_baseurl="", viewer_url=""):
    leaves = [LEAF_UAE, LEAF_FRANCE]
    internals = [PARENT_NODE]
    parent_map = {
        "LEAF_UAE_001": PARENT_NODE,
        "LEAF_FRANCE_001": PARENT_NODE,
        "NODE_ROOT": None,
    }
    return {
        "data": {},
        "tree_root": PARENT_NODE,
        "meta": {},
        "leaves": leaves,
        "internals": internals,
        "all_nodes": leaves + internals,
        "parent_map": parent_map,
        "focal_country": focal,
        "focal_abbr": "UAE",
        "min_conf": min_conf,
        "pdb_baseurl": pdb_baseurl,
        "viewer_url": viewer_url,
        "epitopes": {
            "HA": [
                {"name": "Sa", "start": 128, "end": 175},
                {"name": "RBS", "start": 183, "end": 228},
            ]
        },
        "genome_annotations": {
            "HA": {"type": "CDS", "start": 34, "end": 1710, "strand": "+"},
            "nuc": {"type": "source", "start": 1, "end": 1710, "strand": "+"},
        },
    }


# ---------------------------------------------------------------------------
# Tests: introductions_country plugin
# ---------------------------------------------------------------------------

class TestIntroductionsPlugin(unittest.TestCase):

    def _plugin(self):
        from itol_plugins import introductions_country
        return introductions_country

    def test_output_key_matches_focal_abbr(self):
        ctx = make_ctx()
        result = self._plugin().generate(ctx)
        self.assertIn("dataset_introductions_UAE.txt", result)

    def test_detects_introduction_above_threshold(self):
        """UAE leaf whose parent is France and conf=0.95 should be detected."""
        ctx = make_ctx(min_conf=0.8)
        result = self._plugin().generate(ctx)
        content = result["dataset_introductions_UAE.txt"]
        self.assertIn("LEAF_UAE_001", content)

    def test_no_intro_below_threshold(self):
        """UAE leaf with conf=0.95 should NOT be detected at threshold=0.99."""
        ctx = make_ctx(min_conf=0.99)
        result = self._plugin().generate(ctx)
        content = result["dataset_introductions_UAE.txt"]
        self.assertNotIn("LEAF_UAE_001", content)

    def test_resident_not_detected(self):
        """A France leaf in a France tree should NOT be an introduction."""
        ctx = make_ctx(focal="France")
        result = self._plugin().generate(ctx)
        content = result["dataset_introductions_UAE.txt"]
        # LEAF_FRANCE_001 parent is France (root), so not an intro
        self.assertNotIn("LEAF_FRANCE_001", content)

    def test_colorstrip_header_present(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_introductions_UAE.txt"]
        self.assertIn("DATASET_COLORSTRIP", content)
        self.assertIn("SEPARATOR TAB", content)
        self.assertIn("DATA", content)

    def test_label_uses_ascii_threshold(self):
        """Legend label must use ASCII >= not Unicode >=."""
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_introductions_UAE.txt"]
        self.assertIn(">=", content)
        self.assertNotIn("\u2265", content)  # should not contain ≥


# ---------------------------------------------------------------------------
# Tests: popup_pymol_links plugin
# ---------------------------------------------------------------------------

class TestPopupPlugin(unittest.TestCase):

    def _plugin(self):
        from itol_plugins import popup_pymol_links
        return popup_pymol_links

    def test_output_key(self):
        ctx = make_ctx()
        result = self._plugin().generate(ctx)
        self.assertIn("dataset_popup_info_pymol.txt", result)

    def test_popup_contains_aa_mutations(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("D225G", content)
        self.assertIn("K189N", content)

    def test_popup_contains_nuc_mutations(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("A234T", content)

    def test_popup_marks_introduction(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("INTRODUCTION", content)

    def test_popup_contains_epitope_hit(self):
        """D225G is at position 225 which is within RBS (183-228)."""
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("RBS", content)

    def test_popup_contains_pdb_link(self):
        ctx = make_ctx(pdb_baseurl="https://example.com/pdbs")
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("Download PDB", content)
        self.assertIn("https://example.com/pdbs", content)

    def test_popup_contains_viewer_link(self):
        ctx = make_ctx(
            pdb_baseurl="https://example.com/pdbs",
            viewer_url="https://example.netlify.app/viewer.html",
        )
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("Open 3D Viewer", content)
        self.assertIn("viewer.html", content)

    def test_popup_header_format(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertTrue(content.startswith("POPUP_INFO\n"))
        self.assertIn("SEPARATOR TAB", content)

    def test_popup_no_pdb_when_baseurl_empty(self):
        ctx = make_ctx(pdb_baseurl="")
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertNotIn("Download PDB", content)

    def test_popup_uses_html_tables(self):
        """Popup content should use HTML tables for structured display."""
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("<table", content)
        self.assertIn("<tr>", content)
        self.assertIn("<th>", content)
        self.assertIn("<td>", content)

    def test_popup_has_tpop_wrapper(self):
        """Popup should wrap content in div.tPop for consistent styling."""
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("class='tPop'", content)

    def test_popup_has_section_headings(self):
        """Popup should have clear section h2 headings."""
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("<h2>Metadata</h2>", content)
        self.assertIn("<h2>Introduction inference</h2>", content)
        self.assertIn("<h2>Branch mutations</h2>", content)

    def test_popup_epitope_note_when_no_epitope_tsv(self):
        """When no epitope TSV is provided but genome_annotations exist,
        popup should show a note explaining the limitation."""
        ctx = make_ctx()
        # Override to have no epitopes but have genome_annotations
        ctx["epitopes"] = {}
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("genome_annotations", content)
        self.assertIn("--epitope-tsv", content)

    def test_popup_intro_table_shows_parent_country(self):
        """Introduction table must show parent country."""
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("Parent country", content)
        self.assertIn("France", content)

    def test_popup_intro_table_shows_threshold(self):
        """Introduction table must show the confidence threshold used."""
        ctx = make_ctx(min_conf=0.8)
        content = self._plugin().generate(ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("Threshold", content)
        self.assertIn("0.8", content)


# ---------------------------------------------------------------------------
# Tests: mutation_summary plugin
# ---------------------------------------------------------------------------

class TestMutationSummaryPlugin(unittest.TestCase):

    def _plugin(self):
        from itol_plugins import mutation_summary
        return mutation_summary

    def test_output_key(self):
        ctx = make_ctx()
        result = self._plugin().generate(ctx)
        self.assertIn("dataset_mutation_counts.txt", result)

    def test_heatmap_type(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_mutation_counts.txt"]
        self.assertIn("DATASET_HEATMAP", content)

    def test_counts_present(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_mutation_counts.txt"]
        # LEAF_UAE_001 has 2 nuc + 2 AA mutations
        self.assertIn("LEAF_UAE_001", content)

    def test_field_labels(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_mutation_counts.txt"]
        self.assertIn("Nuc_Muts", content)
        self.assertIn("AA_Muts", content)


# ---------------------------------------------------------------------------
# Tests: attributes_strips plugin
# ---------------------------------------------------------------------------

class TestAttributesStripsPlugin(unittest.TestCase):

    def _plugin(self):
        from itol_plugins import attributes_strips
        return attributes_strips

    def test_country_strip_present(self):
        ctx = make_ctx()
        result = self._plugin().generate(ctx)
        self.assertIn("dataset_country_strip.txt", result)

    def test_country_strip_contains_uae(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_country_strip.txt"]
        self.assertIn("United Arab Emirates", content)

    def test_region_strip_present(self):
        ctx = make_ctx()
        result = self._plugin().generate(ctx)
        self.assertIn("dataset_region_strip.txt", result)

    def test_no_severity_strip_when_absent(self):
        """Severity strip should not be written when no nodes have it."""
        ctx = make_ctx()
        result = self._plugin().generate(ctx)
        self.assertNotIn("dataset_severity_strip.txt", result)


# ---------------------------------------------------------------------------
# Tests: tree_colors_region plugin
# ---------------------------------------------------------------------------

class TestTreeColorsRegionPlugin(unittest.TestCase):

    def _plugin(self):
        from itol_plugins import tree_colors_region
        return tree_colors_region

    def test_output_key(self):
        ctx = make_ctx()
        result = self._plugin().generate(ctx)
        self.assertIn("dataset_region_colors.txt", result)

    def test_colorstrip_type(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_region_colors.txt"]
        self.assertIn("DATASET_COLORSTRIP", content)

    def test_middle_east_present(self):
        ctx = make_ctx()
        content = self._plugin().generate(ctx)["dataset_region_colors.txt"]
        self.assertIn("Middle East", content)


# ---------------------------------------------------------------------------
# Tests: prune_auspice script
# ---------------------------------------------------------------------------

class TestPruneScript(unittest.TestCase):

    def _run_prune(self, tree, keep_attr, keep_values, tmpdir):
        import subprocess
        inp = os.path.join(tmpdir, "test_auspice.json")
        out = os.path.join(tmpdir, "pruned.json")
        auspice = {"meta": {}, "tree": tree}
        with open(inp, "w", encoding="utf-8") as fh:
            json.dump(auspice, fh)
        cmd = [
            sys.executable,
            "scripts/prune_auspice.py",
            "--auspice", inp,
            "--keep-attr", keep_attr,
            "--keep-value",
        ] + list(keep_values) + ["--out", out]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        return result, out

    def _collect_leaf_names(self, node):
        if "children" not in node:
            return [node["name"]]
        names = []
        for c in node.get("children", []):
            names.extend(self._collect_leaf_names(c))
        return names

    def test_keeps_target_country(self):
        import tempfile
        tree = {
            "name": "root",
            "node_attrs": {"country": {"value": "France"}},
            "children": [
                {
                    "name": "UAE_leaf",
                    "node_attrs": {"country": {"value": "United Arab Emirates"}},
                },
                {
                    "name": "France_leaf",
                    "node_attrs": {"country": {"value": "France"}},
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            result, out = self._run_prune(
                tree, "country", ["United Arab Emirates"], tmpdir
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            pruned = json.loads(Path(out).read_text())
            leaves = self._collect_leaf_names(pruned["tree"])
            self.assertIn("UAE_leaf", leaves)
            self.assertNotIn("France_leaf", leaves)

    def test_multiple_values(self):
        import tempfile
        tree = {
            "name": "root",
            "node_attrs": {"country": {"value": "China"}},
            "children": [
                {
                    "name": "UAE_leaf",
                    "node_attrs": {"country": {"value": "United Arab Emirates"}},
                },
                {
                    "name": "France_leaf",
                    "node_attrs": {"country": {"value": "France"}},
                },
                {
                    "name": "China_leaf",
                    "node_attrs": {"country": {"value": "China"}},
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            result, out = self._run_prune(
                tree, "country", ["United Arab Emirates", "France"], tmpdir
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            pruned = json.loads(Path(out).read_text())
            leaves = self._collect_leaf_names(pruned["tree"])
            self.assertIn("UAE_leaf", leaves)
            self.assertIn("France_leaf", leaves)
            self.assertNotIn("China_leaf", leaves)

    def test_error_on_no_match(self):
        import tempfile
        tree = {
            "name": "root",
            "node_attrs": {"country": {"value": "France"}},
            "children": [
                {
                    "name": "France_leaf",
                    "node_attrs": {"country": {"value": "France"}},
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            result, _ = self._run_prune(
                tree, "country", ["United Arab Emirates"], tmpdir
            )
            self.assertNotEqual(result.returncode, 0)


# ---------------------------------------------------------------------------
# Tests: validate_datasets script
# ---------------------------------------------------------------------------

class TestValidateDatasets(unittest.TestCase):

    def _write(self, tmpdir, name, content):
        p = Path(tmpdir) / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_valid_colorstrip(self):
        import tempfile
        content = (
            "DATASET_COLORSTRIP\n"
            "SEPARATOR TAB\n"
            "DATASET_LABEL\tTest\n"
            "COLOR\t#ff0000\n"
            "DATA\n"
            "LEAF_001\t#ff0000\tLabel\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = self._write(tmpdir, "test.txt", content)
            from tests.validate_datasets import validate_file
            errs = validate_file(p)
            self.assertEqual(errs, [])

    def test_invalid_missing_data(self):
        import tempfile
        content = (
            "DATASET_COLORSTRIP\n"
            "SEPARATOR TAB\n"
            "DATASET_LABEL\tTest\n"
            "COLOR\t#ff0000\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = self._write(tmpdir, "test.txt", content)
            from tests.validate_datasets import validate_file
            errs = validate_file(p)
            self.assertTrue(len(errs) > 0)
            self.assertTrue(any("DATA" in e for e in errs))

    def test_invalid_unknown_type(self):
        import tempfile
        content = "UNKNOWN_TYPE\nSEPARATOR TAB\nDATA\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            p = self._write(tmpdir, "test.txt", content)
            from tests.validate_datasets import validate_file
            errs = validate_file(p)
            self.assertTrue(any("Unknown" in e for e in errs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
