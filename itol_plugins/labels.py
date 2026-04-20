"""
Plugin: labels — write a simple LABELS dataset listing all leaf names.

This is the minimal dataset needed for iTOL to recognise node names.
"""


def generate(ctx):
    lines = [
        "LABELS",
        "SEPARATOR TAB",
        "DATA",
    ]
    for node in ctx["leaves"]:
        name = node.get("name", "")
        if name:
            lines.append(name)
    return {"dataset_labels.txt": "\n".join(lines) + "\n"}
