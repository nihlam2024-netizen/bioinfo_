#!/usr/bin/env python3
"""
validate_datasets.py — Validate iTOL dataset files for correct formatting.

Checks that:
  - The dataset type declaration (first line) is a known type
  - Required header directives are present
  - A DATA section exists and is non-empty
  - DATA lines use TAB as separator (where applicable)

Usage:
    python tests/validate_datasets.py out/itol/
    python tests/validate_datasets.py out/itol/dataset_labels.txt
"""
import sys
from pathlib import Path


# Known iTOL dataset types supported by this pipeline
KNOWN_TYPES = frozenset(
    {
        "DATASET_COLORSTRIP",
        "DATASET_HEATMAP",
        "DATASET_TEXT",
        "DATASET_SYMBOL",
        "POPUP_INFO",
        "LABELS",
    }
)

# Required header directives per dataset type (each must appear on its own line)
REQUIRED_HEADERS = {
    "DATASET_COLORSTRIP": ["SEPARATOR", "DATASET_LABEL", "COLOR", "DATA"],
    "DATASET_HEATMAP": [
        "SEPARATOR",
        "DATASET_LABEL",
        "COLOR",
        "FIELD_LABELS",
        "DATA",
    ],
    "POPUP_INFO": ["SEPARATOR", "DATA"],
    "LABELS": ["SEPARATOR", "DATA"],
    "DATASET_TEXT": ["SEPARATOR", "DATASET_LABEL", "DATA"],
    "DATASET_SYMBOL": ["SEPARATOR", "DATASET_LABEL", "DATA"],
}

# Types that do NOT require tab-separated DATA lines
TAB_EXEMPT = frozenset({"LABELS"})


def validate_file(path):
    """Validate a single iTOL dataset file. Returns list of error strings."""
    errors = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read file: {exc}"]

    lines = text.splitlines()
    if not lines:
        return ["File is empty"]

    dtype = lines[0].strip()
    if dtype not in KNOWN_TYPES:
        return [f"Unknown dataset type on first line: {dtype!r}"]

    required = REQUIRED_HEADERS.get(dtype, ["SEPARATOR", "DATA"])
    found_headers = set()
    data_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        for h in required:
            if stripped == h or stripped.startswith(h + "\t") or stripped.startswith(h + " "):
                found_headers.add(h)
        if stripped == "DATA":
            data_idx = i

    for h in required:
        if h not in found_headers:
            errors.append(f"Missing required directive: {h}")

    if data_idx is None:
        errors.append("No DATA section found")
        return errors

    data_lines = [ln for ln in lines[data_idx + 1:] if ln.strip()]
    if not data_lines:
        # Warn but don't fail — dataset may legitimately have no matching nodes
        errors.append("DATA section is empty (no data rows)")
    elif dtype not in TAB_EXEMPT:
        for dl in data_lines[:10]:
            if "\t" not in dl:
                errors.append(
                    f"DATA line appears to lack TAB separator: {dl[:80]!r}"
                )
                break

    return errors


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <dir_or_file> [...]", file=sys.stderr)
        sys.exit(1)

    targets = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            targets.extend(sorted(p.glob("*.txt")))
        elif p.is_file():
            targets.append(p)
        else:
            print(f"WARNING: not found: {p}", file=sys.stderr)

    if not targets:
        print("No .txt files to validate.", file=sys.stderr)
        sys.exit(1)

    all_ok = True
    for f in targets:
        errs = validate_file(f)
        if errs:
            print(f"FAIL  {f}")
            for e in errs:
                print(f"      {e}")
            all_ok = False
        else:
            print(f"OK    {f}")

    print()
    if all_ok:
        print("All datasets are valid.")
        sys.exit(0)
    else:
        print("Some datasets have errors — see above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
