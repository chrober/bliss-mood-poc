"""Offline synthetic English-only Markdown guard tests."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from check_docs_english import failures


class DocumentationLanguageTests(unittest.TestCase):
    def test_flags_german_prose_but_not_identifiers_in_code(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"docs").mkdir()
            (root/"README.md").write_text("# English title\nThis is not a production release.\n")
            (root/"docs"/"a.md").write_text(
                "# English heading\n"
                "The experiment remains unverified.\n"
                "```powershell\n"
                "# Kein deutscher Kommentar wird als Doku-Prosa bewertet.\n"
                "```\n"
                "Use `path/für/file` as a literal identifier.\n"
                "Die Daten sind noch nicht vollständig ausgewertet.\n"
                "The conclusions are still exploratory.\n", encoding="utf-8"
            )
            f=failures(root)
            self.assertEqual(len(f),1)
            self.assertEqual(f[0][0],"docs/a.md")
            self.assertEqual(f[0][1],7)

    def test_current_tree_contains_no_known_german_prose(self):
        self.assertEqual(failures(Path(__file__).resolve().parents[1]), [])


if __name__ == "__main__":
    unittest.main()
