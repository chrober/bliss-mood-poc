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

    def test_only_explicit_operator_guide_is_language_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (root / "README.md").write_text("# English research docs\\n", encoding="utf-8")
            # The pre-existing user-facing export instructions are German.
            (docs / "chatgpt-single-conversation-console-export.md").write_text(
                "Diese Anleitung erklärt einen ChatGPT-Export.\\n", encoding="utf-8")
            (docs / "research-review.md").write_text(
                "This research note is written in English.\\n", encoding="utf-8")
            self.assertEqual(failures(root), [])
            # A German note elsewhere MUST still fail, including adjacent files.
            (docs / "another-guide.md").write_text(
                "Diese Anleitung muss überprüft werden.\\n", encoding="utf-8")
            findings = failures(root)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0][0], "docs/another-guide.md")

    def test_current_tree_contains_no_known_german_prose(self):
        self.assertEqual(failures(Path(__file__).resolve().parents[1]), [])


if __name__ == "__main__":
    unittest.main()
