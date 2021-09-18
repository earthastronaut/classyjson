# Classy Json

Classy json is the best friend to invite to the party. He knows how to check all the other json that comes in and class them up.


# Quick Start

`pip install classyjson`


Create your objects with jsonschema definitions.


``` python
from classyjson import ClassyObject

class Config(ClassyObject):
    schema = {
        "properties": {
            "version": {"type": "string"},
            "verbosity": {"type": "integer"},
            "items": {"type": "array"}
        }
    }


config = Config({
    "version": "v1.0",
    "verbosity": 1,
    "items": [
        1, 2, 3
    ]
})
```
