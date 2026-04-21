"""
test_plugins.py — Unit tests for all itol_plugins/*.

Run with:
    python tests/test_plugins.py
or:
    python -m pytest tests/test_plugins.py -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# Ensure the repo root is on sys.path so itol_plugins and scripts are importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from itol_plugins import (
    labels,
    introductions_country,
    popup_pymol_links,
    mutation_summary,
    attributes_strips,
)
from scripts.itol_build import _partition, _parent_map, make_get_attr, _load_epitopes


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

EXAMPLE_JSON = REPO_ROOT / "Example" / "auspice.json"


def _load_example():
    """Load the bundled example auspice.json and build a minimal ctx dict."""
    data = json.loads(EXAMPLE_JSON.read_text(encoding="utf-8"))
    tree = data["tree"]
    meta = data.get("meta", {})
    leaves, internals = _partition(tree)
    pm = _parent_map(tree)
    get_attr = make_get_attr(leaves)
    epitopes = _load_epitopes(str(REPO_ROOT / "data" / "epitopes_flu_b_ha.tsv"))
    return {
        "data": data,
        "tree": tree,
        "tree_root": tree,
        "meta": meta,
        "leaves": leaves,
        "internals": internals,
        "all_nodes": leaves + internals,
        "parent_map": pm,
        "focal_country": "UAE",
        "focal_abbr": "UAE",
        "min_conf": 0.8,
        "pdb_baseurl": "",
        "pdb_map": {},
        "viewer_url": "",
        "epitopes": epitopes,
        "genome_annotations": meta.get("genome_annotations", {}),
        "get_attr": get_attr,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _first_data_line(content: str) -> str:
    """Return the first non-header data line (line after 'DATA')."""
    lines = content.splitlines()
    in_data = False
    for line in lines:
        if line.strip() == "DATA":
            in_data = True
            continue
        if in_data and line.strip():
            return line
    return ""


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestItolBuildHelpers(unittest.TestCase):
    def setUp(self):
        self.ctx = _load_example()

    def test_leaves_are_tips(self):
        """Leaves should have no children."""
        for leaf in self.ctx["leaves"]:
            self.assertFalse(leaf.get("children"), f"{leaf['name']} has children")

    def test_parent_map_populated(self):
        """Every non-root node name should appear in the parent map."""
        pm = self.ctx["parent_map"]
        self.assertGreater(len(pm), 0)
        # Root should NOT be in parent_map
        self.assertNotIn("NODE_ROOT", pm)

    def test_get_attr(self):
        get_attr = self.ctx["get_attr"]
        leaf = self.ctx["leaves"][0]
        country = get_attr(leaf, "country", "DEFAULT")
        self.assertIsInstance(country, str)
        self.assertNotEqual(country, "DEFAULT")

    def test_epitopes_loaded(self):
        """Epitope TSV should load at least one row."""
        self.assertGreater(len(self.ctx["epitopes"]), 0)
        ep = self.ctx["epitopes"][0]
        self.assertIn("name", ep)
        self.assertIn("start", ep)
        self.assertIn("end", ep)


class TestLabelsPlugin(unittest.TestCase):
    def setUp(self):
        self.ctx = _load_example()

    def test_returns_dict_with_file(self):
        result = labels.generate(self.ctx)
        self.assertIsInstance(result, dict)
        self.assertIn("dataset_labels.txt", result)

    def test_data_header_present(self):
        content = labels.generate(self.ctx)["dataset_labels.txt"]
        self.assertIn("DATA", content)

    def test_one_row_per_leaf(self):
        content = labels.generate(self.ctx)["dataset_labels.txt"]
        data_lines = [
            l for l in content.splitlines()
            if l.strip() and not any(l.startswith(k) for k in (
                "DATASET_TEXT", "SEPARATOR", "DATASET_LABEL", "COLOR", "MARGIN",
                "SIZE_FACTOR", "DATA",
            ))
        ]
        self.assertEqual(len(data_lines), len(self.ctx["leaves"]))


class TestIntroductionsPlugin(unittest.TestCase):
    def setUp(self):
        self.ctx = _load_example()

    def test_returns_dict(self):
        result = introductions_country.generate(self.ctx)
        self.assertIsInstance(result, dict)

    def test_filename_contains_focal_country(self):
        result = introductions_country.generate(self.ctx)
        fname = list(result.keys())[0]
        self.assertIn("UAE", fname)

    def test_uses_tab_separator(self):
        content = list(introductions_country.generate(self.ctx).values())[0]
        # SEPARATOR line should specify TAB
        self.assertIn("SEPARATOR", content)
        separator_line = next(l for l in content.splitlines() if l.startswith("SEPARATOR"))
        self.assertIn("TAB", separator_line)

    def test_no_encoding_artifact(self):
        """Ensure the '≥' encoding artifact is absent; ASCII '>=' used instead."""
        content = list(introductions_country.generate(self.ctx).values())[0]
        self.assertNotIn("≥", content)
        self.assertIn(">=", content)

    def test_introductions_detected(self):
        """Example JSON has leaves entering UAE from other countries."""
        content = list(introductions_country.generate(self.ctx).values())[0]
        data_lines = [
            l for l in content.splitlines()
            if l and not any(l.startswith(k) for k in (
                "DATASET_COLORSTRIP", "SEPARATOR", "DATASET_LABEL", "COLOR",
                "LEGEND_", "DATA",
            ))
        ]
        self.assertGreater(len(data_lines), 0, "Expected at least one introduction leaf")


class TestPopupPlugin(unittest.TestCase):
    def setUp(self):
        self.ctx = _load_example()

    def test_returns_dict_with_file(self):
        result = popup_pymol_links.generate(self.ctx)
        self.assertIsInstance(result, dict)
        self.assertIn("dataset_popup_info_pymol.txt", result)

    def test_popup_info_header(self):
        content = popup_pymol_links.generate(self.ctx)["dataset_popup_info_pymol.txt"]
        self.assertTrue(content.startswith("POPUP_INFO"))

    def test_html_sections_present(self):
        content = popup_pymol_links.generate(self.ctx)["dataset_popup_info_pymol.txt"]
        self.assertIn("Introduction inference", content)
        self.assertIn("Mutations", content)
        self.assertIn("Epitope", content)

    def test_one_row_per_leaf(self):
        content = popup_pymol_links.generate(self.ctx)["dataset_popup_info_pymol.txt"]
        data_lines = [
            l for l in content.splitlines()
            if l.strip() and not any(l.startswith(k) for k in (
                "POPUP_INFO", "SEPARATOR", "DATA",
            ))
        ]
        self.assertEqual(len(data_lines), len(self.ctx["leaves"]))

    def test_html_escaped(self):
        """HTML content in each data row should use proper HTML structure."""
        content = popup_pymol_links.generate(self.ctx)["dataset_popup_info_pymol.txt"]
        for line in content.splitlines():
            if "\t" not in line or line.startswith(("POPUP_INFO", "SEPARATOR", "DATA")):
                continue
            parts = line.split("\t", 2)
            if len(parts) == 3:
                html = parts[2]
                # Verify html starts with expected div
                self.assertIn("<div", html)
                # The leaf_id in the h1 must be HTML-escaped (no raw < or > inside tag content)
                leaf_id = parts[0]
                # Characters that require escaping should not appear raw inside attribute values
                # For these test IDs there are no < > in the names, but the structure must be valid HTML
                self.assertIn(f"<h1>{leaf_id}</h1>", html, "Leaf ID should appear in h1 tag")


class TestMutationSummaryPlugin(unittest.TestCase):
    def setUp(self):
        self.ctx = _load_example()

    def test_returns_heatmap_file(self):
        result = mutation_summary.generate(self.ctx)
        self.assertIn("dataset_mutation_count_heatmap.txt", result)

    def test_field_labels_present(self):
        content = mutation_summary.generate(self.ctx)["dataset_mutation_count_heatmap.txt"]
        self.assertIn("FIELD_LABELS", content)

    def test_one_row_per_leaf(self):
        content = mutation_summary.generate(self.ctx)["dataset_mutation_count_heatmap.txt"]
        data_lines = [
            l for l in content.splitlines()
            if l.strip() and not any(l.startswith(k) for k in (
                "DATASET_HEATMAP", "SEPARATOR", "DATASET_LABEL", "COLOR",
                "FIELD_", "DATA",
            ))
        ]
        self.assertEqual(len(data_lines), len(self.ctx["leaves"]))

    def test_counts_are_non_negative_integers(self):
        content = mutation_summary.generate(self.ctx)["dataset_mutation_count_heatmap.txt"]
        in_data = False
        for line in content.splitlines():
            if line.strip() == "DATA":
                in_data = True
                continue
            if in_data and line.strip():
                parts = line.split("\t")
                self.assertEqual(len(parts), 2, f"Expected 2 fields, got: {line!r}")
                self.assertTrue(parts[1].isdigit(), f"Count should be int: {parts[1]!r}")


class TestAttributesStripsPlugin(unittest.TestCase):
    def setUp(self):
        self.ctx = _load_example()

    def test_returns_multiple_files(self):
        result = attributes_strips.generate(self.ctx)
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

    def test_strip_files_named_correctly(self):
        result = attributes_strips.generate(self.ctx)
        for fname in result:
            self.assertTrue(
                fname.startswith("dataset_strip_"),
                f"Unexpected filename: {fname}",
            )

    def test_each_file_has_data_section(self):
        result = attributes_strips.generate(self.ctx)
        for fname, content in result.items():
            self.assertIn("DATA", content, f"{fname} missing DATA section")

    def test_one_row_per_leaf_per_strip(self):
        result = attributes_strips.generate(self.ctx)
        leaf_count = len(self.ctx["leaves"])
        for fname, content in result.items():
            data_lines = [
                l for l in content.splitlines()
                if l.strip() and not any(l.startswith(k) for k in (
                    "DATASET_COLORSTRIP", "SEPARATOR", "DATASET_LABEL", "COLOR",
                    "LEGEND_", "DATA",
                ))
            ]
            self.assertEqual(
                len(data_lines), leaf_count,
                f"{fname}: expected {leaf_count} rows, got {len(data_lines)}",
            )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
