import unittest
from main import placeholder

class PlaceholderTests(unittest.TestCase):
    def test_placeholder_runs(self) -> None:
        self.assertTrue(placeholder())

if __name__ == "__main__":
    unittest.main()
