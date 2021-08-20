# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=no-self-use

import unittest

from classyjson import (
    jsonschema,
    DotDict,
    ClassyArray,
    ClassyObject,
    ObjectSchema,
)


def _get_example_class_1():
    class MyArrray(ClassyArray):
        schema = {
            "items": {
                "type": "object",
                "properties": {
                    "a1": {"type": ["string", "boolean"]},
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

        def get_k2(self):
            return self.get("k2", [])

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


class TestClassy(unittest.TestCase):
    def _get_example_class(self):
        return _get_example_class_1()

    def test_classy(self):
        classy, data = self._get_example_class()
        obj = classy(data)
        self.assertEqual(obj, data)
        self.assertEqual(obj.k1, data["k1"])
        self.assertEqual(
            obj.k2[0].a1,
            data["k2"][0]["a1"],
        )
        self.assertEqual(
            obj.get_k2(),
            data["k2"],
        )

        self.assertIsInstance(obj, classy)
        self.assertIsInstance(obj.k2, classy.schema["properties"]["k2"])
        self.assertIsInstance(obj.k2[0], DotDict)

    def test_multiple_types(self):
        classy, data = self._get_example_class()
        data["k2"][0]["a1"] = True
        obj = classy(data)
        self.assertEqual(obj, data)

    def test_classy_object_default(self):
        class Obj2(ClassyObject):
            schema = {
                "properties": {
                    "a": {
                        "type": "integer",
                        "default": 0,
                    }
                }
            }

        actual = Obj2()
        self.assertEqual(actual, {"a": 0})

    def test_classy_object_default_classy(self):
        class Obj1(ClassyObject):
            schema = {"properties": {"a": {"type": "object", "default": DotDict()}}}

        class Obj2(ClassyObject):
            schema = {
                "properties": {
                    "a": {
                        "type": "object",
                        "default": Obj1,
                    }
                }
            }

        actual = Obj2()
        self.assertEqual(actual, {"a": {"a": {}}})

    def test_array_items(self):
        classy1, data1 = _get_example_class_1()

        class MyArrItems(ClassyArray):
            scheme = {
                "items": [
                    {"type": "integer"},
                    classy1,
                ]
            }

        data = [
            42,
            data1,
        ]
        obj = MyArrItems(data)
        self.assertEqual(obj, data)

    def test_as_schema(self):
        schema = ObjectSchema(
            properties={
                "a": ClassyObject,
            }
        )
        actual = schema.get_jsonschema()
        expected = {
            "type": "object",
            "properties": {
                "a": {"type": "object"},
            },
        }
        self.assertEqual(actual, expected)

    def test_as_schema_custom(self):
        class MyClassy(ClassyArray):
            schema = {
                "maxLength": 42,
            }

        schema = ObjectSchema(
            properties={
                "a": MyClassy,
            }
        )
        actual = schema.get_jsonschema()
        expected = {
            "type": "object",
            "properties": {
                "a": {"type": "array", "maxLength": 42},
            },
        }
        self.assertEqual(actual, expected)


class TestClassySchemaValidation(unittest.TestCase):
    def setUp(self):
        if jsonschema is None:
            self.skipTest("jsonschema required for validation")

    def test_classy_required(self):
        classy, data = _get_example_class_1()
        data.pop("k1")
        self.assertRaises(
            jsonschema.exceptions.ValidationError,
            classy,
            data,
        )

    def test_classy_wrong_name_type(self):
        classy, data = _get_example_class_1()
        data["k1"] = 1.2345
        self.assertRaises(
            jsonschema.exceptions.ValidationError,
            classy,
            data,
        )

    def test_classy_nested_check(self):
        classy, data = _get_example_class_1()
        data["k2"][1]["a2"] = "this should be a number"
        self.assertRaises(
            jsonschema.exceptions.ValidationError,
            classy,
            data,
        )


if __name__ == "__main__":
    unittest.main()
