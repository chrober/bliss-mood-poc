#!/usr/bin/env python3
"""Fail when repository Markdown prose contains high-confidence German phrases.

Markdown documentation is English-only. Fenced code (including PowerShell)
and inline code/links may contain source identifiers that are not prose.
This conservative guard detects accidental German paragraphs or headings;
it is not a machine translation or general language classifier.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

# High-confidence German prose words, rather than names, acronyms or
# ambiguous technical terms ("die", "den", "im", "ist").
GERMAN = re.compile(
    r"\b(?:und|nicht|fuer|für|keine|keinen|keiner|dass|"
    r"dieser|diese|diesen|dieses|einen|einer|einem|"
    r"wurde|wurden|bereits|zunächst|anschließend|"
    r"ausschließlich|entsprechend|gegenüber|"
    r"vollständig|ursprünglich|unverändert|"
    r"überprüfen|geprüft|müssen|können|"
    r"verifiziert|nachfolgend|weiterhin|"
    r"Hörtest|Forschungsfrage|Auswertung|"
    r"Prüfgates|Ergebnisse|Kohorte|"
    r"Quellenprüfung|Künstler|"
    r"erledigt|einheitlich)\b",
    flags=re.IGNORECASE,
)
FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})")
INLINE = re.compile(r"`[^`]*`")
URL = re.compile(r"https?://\S+")


def failures(root: Path) -> list[tuple[str, int, str]]:
    """Return filename/line/content for likely non-English Markdown prose."""
    paths = [root / "README.md", *sorted((root / "docs").rglob("*.md"))]
    problems = []
    for path in paths:
        if not path.is_file():
            continue
        fence = False
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE.match(raw):
                fence = not fence
                continue
            if fence:
                continue
            # Ignore literal source identifiers, but check surrounding words.
            prose = INLINE.sub("", URL.sub("", raw))
            if GERMAN.search(prose):
                problems.append((str(path.relative_to(root)), lineno, raw.strip()[:220]))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    found = failures(args.root)
    for path, line, source in found:
        print(f"{path}:{line}: likely German prose: {source}")
    if found:
        print(f"Documentation English-only check FAILED: {len(found)} flagged lines")
        return 1
    count = int((args.root / "README.md").is_file()) + len(list((args.root / "docs").rglob("*.md")))
    print(f"Documentation English-only check PASS: {count} Markdown files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
