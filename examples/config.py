""" Example of writing a config file which is parsed by json
"""
import logging

import classyjson


class ConfigV1(classyjson.ClassyObject):
    """v1 of our config"""

    schema = {
        "properties": {
            "version": {"type": "string"},
            "verbosity": {"type": "integer"},
        }
    }


class ConfigLogging(classyjson.ClassyObject):
    """Logging configuration"""

    schema = {
        "properties": {
            "loglevel": {
                "type": "string",
                "default": "info",
                "enum": ["info", "debug", "critical"],
            }
        }
    }
    __slots__ = ["loglevel"]  # allows most editors to provide suggestions

    def __init__(self, instance, validate=True):
        """Initialize logging"""
        super().__init__(instance, validate=validate)
        logging.getLogger().setLevel(self.loglevel.upper())


class ConfigV2(ConfigV1):
    """v2 of our config"""

    schema = {
        "properties": {
            "version": {
                "type": "string",
            },
            "items": {
                "type": "array",
            },
            "logging": ConfigLogging,
        }
    }


VERSIONS = {
    "v1": ConfigV1,
    "v2": ConfigV2,
}


def parse_config(json_data):
    """Parse our configuration"""
    return classyjson.load(
        json_data,
        classy_options=("version", VERSIONS),
    )


if __name__ == "__main__":
    data_config_v1 = {"version": "v1", "verbosity": 1}
    config_v1 = parse_config(data_config_v1)
    print(
        "config_v1",
        config_v1.version,
        config_v1.verbosity,
        config_v1["verbosity"],
    )

    data_config_v2 = {
        "version": "v2",
        "items": [1, 2, 3],
        "logging": {"loglevel": "info"},
    }
    config_v2 = parse_config(data_config_v2)
    print(
        "config_v2",
        config_v2["version"],
        config_v2.version,
        config_v2.logging.loglevel,
    )
