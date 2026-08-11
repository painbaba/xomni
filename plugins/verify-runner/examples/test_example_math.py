"""Unit tests for ``example_math`` — the verify-runner example project."""

import unittest

from example_math import add, is_even


class TestAdd(unittest.TestCase):
    """Tests for the ``add`` function."""

    def test_add_positive(self) -> None:
        self.assertEqual(add(2, 3), 5)

    def test_add_negative(self) -> None:
        self.assertEqual(add(-1, 1), 0)


class TestIsEven(unittest.TestCase):
    """Tests for the ``is_even`` function."""

    def test_is_even_true(self) -> None:
        self.assertTrue(is_even(4))

    def test_is_even_false(self) -> None:
        self.assertFalse(is_even(7))


if __name__ == "__main__":
    unittest.main()
