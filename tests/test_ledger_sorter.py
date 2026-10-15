import tempfile
import unittest
from pathlib import Path

from shoebox import ledger
from shoebox.ollama import has_model
from shoebox.schema import Receipt
from shoebox.sorter import destination, place


def make(**kw):
    base = dict(sha256="x", filename="f.txt", vendor="Figma", date="2026-02-14",
                total=15.0, tax=0.0, currency="USD", category="software", doc_type="receipt")
    base.update(kw)
    return Receipt(**base)


class SorterTests(unittest.TestCase):
    def test_destination_layout(self):
        dest = destination(make(), Path("out"), ".PDF")
        self.assertEqual(dest, Path("out/2026-02/software/2026-02-14_figma_15.00.pdf"))

    def test_undated_goes_to_undated(self):
        dest = destination(make(date="", total=None), Path("out"), ".txt")
        self.assertEqual(dest, Path("out/undated/software/undated_figma_unknown.txt"))

    def test_collision_gets_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "a.txt"
            src.write_text("hi")
            first = place(src, make(), tmp / "sorted")
            second = place(src, make(), tmp / "sorted")
            self.assertNotEqual(first, second)
            self.assertTrue(first.exists() and second.exists() and src.exists())


class LedgerTests(unittest.TestCase):
    def test_roundtrip_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            rows = [make(), make(vendor="Delta", category="travel", total=300.0, sha256="y")]
            ledger.save(path, rows)
            loaded = ledger.load(path)
            self.assertEqual(len(loaded), 2)
            text = ledger.render_summary(loaded)
            self.assertIn("315.00 USD", text)
            self.assertIn("| travel | 300.00 USD |", text)

    def test_missing_fields_flagged(self):
        text = ledger.render_summary([make(date="", filename="blurry.png")])
        self.assertIn("blurry.png", text)


class OllamaHelperTests(unittest.TestCase):
    def test_has_model(self):
        installed = ["gemma3:4b", "llama3.2:latest"]
        self.assertTrue(has_model(installed, "gemma3:4b"))
        self.assertTrue(has_model(installed, "llama3.2"))
        self.assertFalse(has_model(installed, "gemma3:12b"))


if __name__ == "__main__":
    unittest.main()
