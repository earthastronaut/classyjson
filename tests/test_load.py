# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

import unittest

import classyjson
from classyjson import ClassyObject


class TestDefaultJsonLoad(unittest.TestCase):
    def test_str_int_float(self):
        actual = classyjson.load("1")
        self.assertEqual(actual, 1)

        actual = classyjson.load("1.123")
        self.assertEqual(actual, 1.123)

        actual = classyjson.load('"hello"')
        self.assertEqual(actual, "hello")

    def test_load_classy(self):
        class MyClassy(ClassyObject):
            schema = {"properties": {"k1": {"type": "integer"}}}

        obj = classyjson.load(
            '{"k1": 1}',
            classy=MyClassy,
        )
        self.assertIsInstance(obj, MyClassy)
        self.assertEqual(obj, {"k1": 1})

    def test_load_classy_object(self):
        obj = classyjson.load(
            '{"k1": 1}',
            classy=ClassyObject,
        )
        self.assertIsInstance(obj, ClassyObject)
        self.assertEqual(obj, {"k1": 1})


if __name__ == "__main__":
    unittest.main()
