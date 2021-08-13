# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

import unittest

try:
    import jsonschema
except ImportError:
    jsonschema = None

from classyjson import (
    ClassyArray,
    ClassyObject,
)


class TestClassy(unittest.TestCase):
    def _get_example_class(self):
        class MyArrray(ClassyArray):
            schema = {
                "items": {
                    "type": "object",
                    "properties": {
                        "a1": {"type": "string"},
                        "a2": {"type": "number"},
                    },
                }
            }

        class MyObj(ClassyObject):
            schema = {
                "required": ["k1"],
                "properties": {
                    "k1": {"type": "string"},
                    "k2": MyArrray,
                },
            }

        data = {
            "k1": "foo",
            "k2": [
                {
                    "a1": "bar",
                    "a2": 2.34,
                },
                {
                    "a1": "classy",
                },
            ],
        }

        return MyObj, data

    def test_classy(self):
        classy, data = self._get_example_class()
        obj = classy(data)
        self.assertEqual(obj, data)
        self.assertEqual(obj.k1, data["k1"])
        self.assertEqual(
            obj.k2[0].a1,
            data["k2"][0]["a1"],
        )


if __name__ == "__main__":
    unittest.main()
