import unittest

from shoebox.schema import Receipt, normalize_currency, parse_amount, parse_date, slugify


class ParseAmountTests(unittest.TestCase):
    def test_plain_numbers(self):
        self.assertEqual(parse_amount(12.5), 12.5)
        self.assertEqual(parse_amount("42"), 42.0)

    def test_us_and_eu_formats(self):
        self.assertEqual(parse_amount("$1,234.50"), 1234.5)
        self.assertEqual(parse_amount("1.234,50 €"), 1234.5)
        self.assertEqual(parse_amount("1,50"), 1.5)
        self.assertEqual(parse_amount("1,234"), 1234.0)

    def test_garbage(self):
        self.assertIsNone(parse_amount(""))
        self.assertIsNone(parse_amount(None))
        self.assertIsNone(parse_amount("n/a"))


class ParseDateTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(parse_date("2026-03-09"), "2026-03-09")
        self.assertEqual(parse_date("09/03/2026"), "2026-03-09")
        self.assertEqual(parse_date("March 9, 2026"), "2026-03-09")

    def test_unknown(self):
        self.assertEqual(parse_date("sometime"), "")
        self.assertEqual(parse_date(None), "")


class MiscTests(unittest.TestCase):
    def test_currency(self):
        self.assertEqual(normalize_currency("€"), "EUR")
        self.assertEqual(normalize_currency("usd"), "USD")
        self.assertEqual(normalize_currency("dollars"), "")

    def test_slug(self):
        self.assertEqual(slugify("Café & Co. Ltd!"), "caf-co-ltd")
        self.assertEqual(slugify("???"), "unknown")

    def test_from_model_falls_back_safely(self):
        r = Receipt.from_model(
            {"vendor": "", "date": "bad", "total": "N/A", "category": "yachts", "doc_type": "x"},
            "a.txt",
            "abc",
        )
        self.assertEqual(r.vendor, "unknown")
        self.assertEqual(r.date, "")
        self.assertIsNone(r.total)
        self.assertEqual(r.category, "other")
        self.assertEqual(r.doc_type, "other")


if __name__ == "__main__":
    unittest.main()
