# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

import unittest

import classyjson


class TestDefaultJsonLoad(unittest.TestCase):
    def test_str_int_float(self):
        actual = classyjson.load("1")
        self.assertEqual(actual, 1)

        actual = classyjson.load("1.123")
        self.assertEqual(actual, 1.123)

        actual = classyjson.load('"hello"')
        self.assertEqual(actual, "hello")


if __name__ == "__main__":
    unittest.main()
