# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

import unittest

from classyjson import DotDict


class TestDotDict(unittest.TestCase):
    def test_typing(self):
        data = {"hello": "world"}
        actual = DotDict(data)
        self.assertIsInstance(actual, dict)
        self.assertIsInstance(actual, DotDict)
        self.assertEqual(actual, data)
        actual.update(data)

        self.assertTrue(hasattr(actual, "hello"))
        self.assertTrue(actual.hello, "world")

    def test_subdicts(self):
        data = {"foo": {"foo": "bar"}}
        actual = DotDict(data)
        self.assertEqual(actual, data)
        self.assertIsInstance(actual.foo, DotDict)

    def test_subdicts_list(self):
        data = {"foo": [{"foo": "bar"}, {"fofo": "baba"}]}
        actual = DotDict(data)
        self.assertIsInstance(actual.foo, list)
        self.assertIsInstance(actual.foo[0], DotDict)
        self.assertEqual(actual.foo[0].foo, "bar")
        self.assertEqual(actual, data)

    def test_update(self):
        actual = DotDict({"foo": [{"foo": "bar"}, {"fofo": "baba"}]})

        data = {"foo": [{"foo": "bar2"}, {"fofo": "baba2"}]}
        actual.update(data)
        self.assertIsInstance(actual.foo, list)
        self.assertIsInstance(actual.foo[0], DotDict)
        self.assertEqual(actual.foo[0].foo, "bar")
        self.assertEqual(actual, data)

    def test_subdicts_tuple(self):
        data = {"foo": ({"foo": "bar"}, {"fofo": "baba"})}
        actual = DotDict(data)
        self.assertIsInstance(actual.foo, tuple)
        self.assertIsInstance(actual.foo[0], DotDict)
        self.assertEqual(actual.foo[0].foo, "bar")
        self.assertEqual(actual, data)

    def test_subdicts_custom_iterable(self):
        class MyList(list):
            """Subclass"""

        data = {"foo": MyList([{"foo": "bar"}, {"fofo": "baba"}])}
        actual = DotDict(data)
        self.assertIsInstance(actual.foo, MyList)
        self.assertIsInstance(actual.foo[0], DotDict)
        self.assertEqual(actual.foo[0].foo, "bar")
        self.assertEqual(actual, data)

    def test_invalid_attrs(self):
        data = {
            "234": "its a number",
            "0x123": "whoop",
            (1, 2): "hmmm tuple",
            2.345: "it's a float",
            "_conflict": "underscores?",
            "__gt__": "gt",
            "_overwrite_attrs": "haha",
            "and... space": "string gotta space",
            "and/slash": "string gotta slash",
            "and\n\tspecial": "string gotta special character",
        }
        actual = DotDict(data)
        self.assertNotEqual(actual.__gt__, data["__gt__"])
        self.assertEqual(actual["__gt__"], data["__gt__"])
        self.assertNotEqual(actual._overwrite_attrs, "haha")
        self.assertEqual(actual, data)

    def test_overwrite_attrs(self):
        data = {
            "items": "haha not a function",
            "keys": "haha not a function",
        }
        actual = DotDict(data)
        self.assertEqual(actual, data)
        self.assertNotEqual(actual.items, data["items"])
        self.assertNotEqual(actual.keys, data["keys"])

    def test_deleting(self):
        data = {"hello": "world", "foo": "bar"}
        actual = DotDict(data)

        data.pop("hello")
        del actual["hello"]
        self.assertEqual(actual, data)

        data.pop("foo")
        del actual.foo
        self.assertEqual(actual, data)

    def test_pop(self):
        data = {"hello": "world", "foo": "bar"}
        actual = DotDict(data)

        data.pop("hello")
        actual.pop("hello")
        self.assertEqual(actual, data)
        self.assertTrue(not hasattr(actual, "hello"))

    def test_overwriter(self):
        class OverwriteDotDict(DotDict):
            _overwrite_attrs = True

        obj = OverwriteDotDict({"items": "bwahaha"})
        self.assertEqual(obj.items, "bwahaha")

    def test_setdefault(self):
        obj = DotDict({"a": 1})
        obj.setdefault("a", 2)
        self.assertEqual(obj.a, 1)
        obj.setdefault("b", 3)
        self.assertEqual(obj.b, 3)


if __name__ == "__main__":
    unittest.main()
