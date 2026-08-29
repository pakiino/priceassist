import unittest
from pricing import get_price_stats


class PricingTests(unittest.TestCase):
    def test_known_value_steam_deck_512gb_loose(self):
        # hand-verified against data/raw_sold_listings_all.csv
        median, min_price, max_price = get_price_stats("Steam Deck OLED", "512GB", "Loose")
        self.assertAlmostEqual(median, 649.995)
        self.assertLessEqual(min_price, median)
        self.assertLessEqual(median, max_price)

    def test_handles_a_combo_with_exactly_ten_rows(self):
        # New Nintendo 3DS XL - Hyrule Edition / standard / CIB has exactly
        # 10 matching rows in the dataset -- exercises the "fewer than 10
        # exist" boundary using real data instead of fabricated data.
        median, min_price, max_price = get_price_stats(
            "New Nintendo 3DS XL - Hyrule Edition", "standard", "CIB"
        )
        self.assertIsNotNone(median)
        self.assertLessEqual(min_price, median)
        self.assertLessEqual(median, max_price)

    def test_min_median_max_ordering_holds_for_every_real_combo(self):
        # sanity check across every item/variant/completeness combo actually
        # present in the dataset, not just one hand-picked example
        combos = [
            ("Steam Deck OLED", "512GB", "Loose"),
            ("Steam Deck OLED", "512GB", "CIB"),
            ("Steam Deck OLED", "1TB", "Loose"),
            ("Steam Deck OLED", "1TB", "CIB"),
            ("Nintendo Switch OLED - Tears of the Kingdom Edition", "standard", "Loose"),
            ("Nintendo Switch OLED - Tears of the Kingdom Edition", "standard", "CIB"),
            ("New Nintendo 3DS XL - Hyrule Edition", "standard", "Loose"),
            ("New Nintendo 3DS XL - Hyrule Edition", "standard", "CIB"),
        ]
        for model, variant, completeness in combos:
            with self.subTest(model=model, variant=variant, completeness=completeness):
                median, min_price, max_price = get_price_stats(model, variant, completeness)
                self.assertLessEqual(min_price, median)
                self.assertLessEqual(median, max_price)


if __name__ == "__main__":
    unittest.main()
