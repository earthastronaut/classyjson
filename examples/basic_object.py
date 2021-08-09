""" Shows a simple example of one class object
"""
# standard
import json

# internal
import classyjson  # pylint: disable=import-error


class MyJsonData(classyjson.ObjectJson):
    """Basic object type"""

    schema = {
        "type": "object",  # (optional), will be inferred from class
        "properties": {  # properties are required
            "planet": {"type": "string"},
            "age": {"type": "integer"},
            "contenents": {
                "type": "array",
                "items": {
                    "name": {"type", "string"},
                },
            },
            "info": {
                "type": "object",
                "properties": {
                    "population": {"type": "number"},
                    "planet_type": {"type": "string"},
                },
            },
        },  # optional, along with other jsonschema keys
        "requires": ["planet"],
    }


if __name__ == "__main__":
    json_data = {
        "planet": "earth",
        "age": 4.56e6,
        "info": {
            "population": 7e9,
        },
    }

    # parse json, validate with jsonschema, and return object
    data = MyJsonData(json_data)

    print(
        data.planet,
        data.age,
        data["planet"],
        data["age"],
        data["info"],
        data.info.population,
    )

    print(dict(**data))
    print(json.dumps(data, indent=2))
