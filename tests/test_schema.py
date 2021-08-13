# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=invalid-name,no-self-use

import unittest

from classyjson import (
    jsonschema,
    JSON_TYPE_STR,
    JSON_TYPE_INTEGER,
    JSON_TYPE_NUMBER,
    JSON_TYPE_ARRAY,
    BaseSchema,
    StrSchema,
    IntSchema,
    NumberSchema,
    BoolSchema,
    NullSchema,
    ObjectSchema,
    ArraySchema,
)


class TestSchema(unittest.TestCase):
    def test_basic_schema_creation(self):
        schema = ObjectSchema(
            required=["k1", "k2"],
            properties={
                "k1": StrSchema(
                    format="date-time",
                ),
                "k2": IntSchema(),
                "k3": NumberSchema(),
                "k4": ArraySchema(
                    items=IntSchema(),
                ),
                "k5": NullSchema(),
                "k6": BoolSchema(),
            },
        )
        expected = {
            "type": "object",
            "required": ["k1", "k2"],
            "properties": {
                "k1": {"type": "string", "format": "date-time"},
                "k2": {"type": "integer"},
                "k3": {"type": "number"},
                "k4": {
                    "type": "array",
                    "items": {"type": "integer"},
                },
                "k5": {"type": "null"},
                "k6": {"type": "boolean"},
            },
        }
        self.assertEqual(schema, expected)
        actual = schema.get_jsonschema()
        self.assertIsInstance(actual, dict)
        self.assertEqual(actual, expected)

    def test_schema_add(self):
        s1 = IntSchema()
        s2 = StrSchema(format="date-time")
        actual = s1 + s2

        actual.validate("2")
        actual.validate('"2021-01-01"')

        expected = {
            "type": {
                JSON_TYPE_INTEGER,
                JSON_TYPE_STR,
            },
            "format": "date-time",
        }
        actual["type"] = set(actual["type"])
        self.assertEqual(actual, expected)

    def test_schema_add_multiple_types(self):
        s1 = IntSchema()
        s2 = StrSchema(format="date-time")
        s3 = StrSchema(format="email")
        actual = (s1 + s2) + s3

        actual.validate("2")
        actual.validate('"hello@example.com"')

        expected = {
            "type": {
                JSON_TYPE_INTEGER,
                JSON_TYPE_STR,
            },
            "format": "email",
        }
        actual["type"] = set(actual["type"])
        self.assertEqual(actual, expected)

    def test_schema_add_array(self):
        s1 = IntSchema()
        s2 = StrSchema(format="date-time")
        s3 = ArraySchema(items=NumberSchema())
        actual = s1 + s2 + s3

        actual.validate("2")
        actual.validate('"2021-01-01"')
        actual.validate("[1, 2, 3]")

        expected = {
            "type": {
                JSON_TYPE_INTEGER,
                JSON_TYPE_STR,
                JSON_TYPE_ARRAY,
            },
            "format": "date-time",
            "items": {"type": JSON_TYPE_NUMBER},
        }
        actual["type"] = set(actual["type"])
        self.assertEqual(actual, expected)


class TestSchemaLoad(unittest.TestCase):
    def _get_example_1(self):
        schema = ObjectSchema(
            required=["k1", "k2"],
            properties={
                "k1": StrSchema(
                    format="date-time",
                ),
                "k2": IntSchema() + NullSchema(),
                "k3": NumberSchema(),
                "k4": ArraySchema(
                    items=ObjectSchema(
                        properties={
                            "s1": StrSchema(
                                maxLength=5,
                            ),
                            "s3": BoolSchema(),
                        }
                    ),
                ),
            },
        )
        data = {
            "k1": "2021-01-01",  # datetime
            "k2": 3,  # integer
            # k3: there is no k3
            "k4": [
                {
                    "s1": "hello",
                    "s3": True,
                },
                {
                    "s1": "hello",
                },
            ],
        }
        return schema, data

    def test_load(self):
        schema, data = self._get_example_1()
        actual = schema.load(data)
        self.assertEqual(actual, data)

    def test_load_optional(self):
        schema, data = self._get_example_1()
        data["k2"] = None
        actual = schema.load(data)
        self.assertEqual(actual, data)

    def test_load_missing_required(self):
        if jsonschema is None:
            self.skipTest("jsonschema required")
        schema, data = self._get_example_1()
        data.pop("k1")
        self.assertRaises(
            jsonschema.exceptions.ValidationError,
            schema.load,
            data,
        )

    def test_unknown(self):
        self.assertRaises(
            LookupError,
            BaseSchema,
            type="blah",
        )

        self.assertRaises(
            LookupError,
            BaseSchema,
            type=["string", "blah"],
        )

        self.assertRaises(
            TypeError,
            BaseSchema,
            type={},
        )


if __name__ == "__main__":
    unittest.main()
