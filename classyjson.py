""" General class objects for writing the parameters out. Does not have specific
logic for a particular parameters schema.
"""
# flake8: noqa: E501
# standard
from collections.abc import Iterable
import logging
from typing import Any, Tuple, Dict, Union, KT, VT
import json
import io
import os

# external
import jsonschema


logger = logging.getLogger(__name__)


__all__ = [
    "BaseJson",
    "ObjectJson",
    "ArrayJson",
    "load",
    "loads",
    "dump",
    "dumps",
]


JSON_TYPE_STR = "string"
JSON_TYPE_NUMBER = "number"
JSON_TYPE_INTEGER = "integer"
JSON_TYPE_OBJECT = "object"
JSON_TYPE_ARRAY = "array"
JSON_TYPE_BOOL = "boolean"
JSON_TYPE_NULL = "null"
JSON_TYPE_DATETIME = "datetime"


TJsonTypes = Union[str, float, int, dict, list, bool, type(None)]


def _inf_item_generator(item):
    """Return this item"""
    while True:
        yield item


class MetaBaseJson(type):
    """Metadata class for checking the schema on the class"""

    def __init__(cls, name, bases, dict_):
        if not isinstance(cls.schema, dict):
            raise TypeError("Class must define schema as dict")
        cls.schema.setdefault("type", cls._schema_type)
        super().__init__(name, bases, dict_)


class BaseJson(metaclass=MetaBaseJson):
    """Python JSON Schema class object"""

    _schema_type = None
    schema = {}

    @classmethod
    def get_jsonschema(cls: object) -> object:
        """Generate the full jsonschema"""
        return cls.schema.copy()

    @classmethod
    def _validate(cls: object, instance: TJsonTypes, **kws):
        """Validate instance against schema"""
        schema = cls.get_jsonschema()
        jsonschema.validate(instance, schema, **kws)

    @classmethod
    def _parse(cls, instance: Dict[str, Any], validate: bool = True) -> Any:
        if validate:
            cls._validate(instance)
        return instance


class BaseObjectJson(BaseJson):
    """Use with "type": "object" where all "properties" are known."""

    _schema_type = JSON_TYPE_OBJECT
    __slots__ = []

    @classmethod
    def _schema_properties(cls):
        return cls.schema.get("properties", {})

    @classmethod
    def get_jsonschema(cls: object) -> object:
        """Generate the full jsonschema"""
        schema = cls.schema.copy()
        properties = {}
        for key, prop in schema.get("properties", {}).items():
            if isinstance(prop, type) and issubclass(prop, BaseJson):
                prop_schema = prop.get_jsonschema()
            else:
                prop_schema = prop
            properties[key] = prop_schema
        schema["properties"] = properties
        return schema

    @classmethod
    def _parse(cls, instance: Dict[str, Any], validate: bool = True) -> Dict:
        instance = super()._parse(instance, validate=validate)
        if not isinstance(instance, dict):
            raise TypeError(f"Wrong instance base type: {type(instance)}")

        props = cls._schema_properties()
        data = {}
        for prop_key, prop_schema in props.items():
            if prop_key not in instance:
                data[prop_key] = None
                continue
            inst = instance[prop_key]
            prop_type = prop_schema["type"]
            if isinstance(prop_type, type) and issubclass(prop_type, BaseJson):
                classy = prop_type
                value = classy(inst, validate=False)
            else:
                value = inst
            data[prop_key] = value
        return data


class DotDict(dict):
    """dot.notation access to dictionary keys"""

    def __init__(self, *args, **kws):
        super().__init__()
        self._dictclass = self.__class__
        self.update(*args, **kws)

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def __getitem__(self, name: KT):
        try:
            return super().__getitem__(name)
        except KeyError as error:
            names = list(self.keys())
            error.args = (f"'{name}' not in {names}",)
            raise error

    def __setitem__(self, name: str, value: VT):
        # modify type on set
        if type(value) == dict:  # pylint: disable=unidiomatic-typecheck
            value_dotdict = self._dictclass(value)
        else:
            value_dotdict = value
        self.__dict__[name] = value_dotdict
        return super().__setitem__(name, value)

    def setdefault(self, key: KT, default: VT) -> VT:
        if key not in self:
            self[key] = default
        return self[key]

    def update(self, *args, **kws):
        for arg in args:
            kws.update(arg)
        for key, value in kws.items():
            self[key] = value
        return self

    def __delitem__(self, name: str):
        del self.__dict__[name]
        return super().__delitem__(name)

    def __setattr__(self, name: str, value: VT):
        """Use __setitem__"""
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self.__setitem__(name, value)

    def __getattr__(self, name: str):
        """Use __getitem__"""
        if name.startswith("_"):
            return super().__getattribute__(name)
        try:
            return self.__getitem__(name)
        except KeyError as error:
            raise AttributeError(
                f"{name} not in {tuple(self.__dict__.keys())}"
            ) from error

    def __hasattr__(self, name: str):
        """Use __contains__"""
        return super().__contains__(name)

    def __delattr__(self, name: str):
        """Use __delitem__"""
        return self.__delitem__(name)


class ObjectJson(BaseObjectJson, DotDict):
    """Json Schema type 'object' """

    @classmethod
    def _parse(cls, instance: Dict[str, Any], validate: bool = True) -> Dict:
        data = super()._parse(instance, validate=validate)

        def _convert_to_class(obj):
            if isinstance(obj, dict):
                return DotDict(
                    {key: _convert_to_class(value) for key, value in obj.items()}
                )
            elif isinstance(obj, str):
                return obj
            elif isinstance(obj, Iterable):
                return obj.__class__(*(_convert_to_class(element) for element in obj))
            else:
                return obj

        data_converted = _convert_to_class(data)
        return data_converted

    def __init__(self, instance: Dict[str, Any], validate: bool = True):
        super().__init__()
        self._dictclass = DotDict
        data = self._parse(instance, validate=validate)
        self.update(data)


class BaseArrayJson(BaseJson):
    """Json Schema type 'array' """

    _schema_type = JSON_TYPE_ARRAY

    @classmethod
    def _schema_items(cls):
        return cls.schema.get("items")

    @classmethod
    def _schema_contains(cls):
        return cls.schema.get("contains")

    @classmethod
    def get_jsonschema(cls: object) -> object:
        """Generate the full jsonschema"""
        schema = cls.schema.copy()

        items = schema.get("items")
        if isinstance(items, type) and issubclass(items, BaseJson):
            schema["items"] = items.get_jsonschema()
        elif isinstance(items, list):
            items_schema = []
            for item in items:
                if isinstance(item, type) and issubclass(item, BaseJson):
                    items_schema.append(item.get_jsonschema)
                else:
                    items_schema.append(dict(item))
            schema["items"] = items_schema
        elif items is not None:
            schema["items"] = items
        return schema

    @classmethod
    def _parse(cls, instance: Dict[str, Any], validate: bool = True) -> Dict:
        instance = super()._parse(instance, validate=validate)
        if not isinstance(instance, list):
            raise TypeError(f"Instance must be of base type list not {type(instance)}")

        schema_items = cls._schema_items()
        if isinstance(schema_items, dict):
            schema_items_iter = _inf_item_generator(schema_items)
        elif isinstance(schema_items, list):
            schema_items_iter = schema_items
        else:
            schema_items_iter = _inf_item_generator(None)
        items = []
        for schema_item, inst in zip(schema_items_iter, instance):
            item_type = schema_item["type"]
            if isinstance(item_type, type) and issubclass(item_type, BaseJson):
                classy = item_type
                value = classy(inst, validate=False)
                items.append(value)

            else:
                items.append(inst)
        return items


class ArrayJson(BaseJson, list):
    """Json Schema type 'array' """

    def __init__(self, instance: TJsonTypes, validate: bool = True):
        items = self._parse(instance, validate=validate)
        super().__init__(items)


TJsonTypes = Union[str, float, int, dict, list, bool, type(None)]


def _load_json(
    json_data: Union[str, Dict, io.BufferedReader],
    **kws,
) -> TJsonTypes:
    """Wrapper around json.load which handles overloaded json types"""
    if isinstance(json_data, dict):
        return json_data
    elif isinstance(json_data, str):
        if os.path.exists(json_data):
            with open(json_data) as buffer:
                json_loaded = json.load(buffer, **kws)
        else:
            json_loaded = json.loads(json_data, **kws)
        return json_loaded
    elif isinstance(json_data, io.BufferedReader):
        return json.load(json_data, **kws)
    else:
        raise TypeError(f"Invalid type {type(json_data)}")


def load(
    json_data: Union[str, Dict, io.BufferedReader],
    classy: BaseJson = None,
    classy_options: Tuple[str, Dict[str, BaseJson]] = None,
    **kws,
) -> BaseJson:
    """Load generic."""
    json_loaded = _load_json(json_data, **kws)

    if classy_options is not None:
        keyword, options = classy_options
        if not isinstance(json_loaded):
            raise TypeError(
                f"classy_options can only be used for dict, not {type(json_loaded)}"
            )
        name = json_loaded[keyword]
        try:
            classy = options[name]
        except KeyError as error:
            raise KeyError(f"{name} not in {options.keys()}") from error

    if classy is None:  # no schema
        return json_loaded
    else:
        return classy(json_loaded)


def loads(
    json_data: str,
    classy: BaseJson = None,
    classy_options: Tuple[str, Dict[str, BaseJson]] = None,
) -> BaseJson:
    """Load from string"""
    return load(
        json_data,
        classy=classy,
        classy_options=classy_options,
    )


def dump(
    obj: Union[BaseJson, TJsonTypes],
    fp: Union[str, io.BufferedWriter] = None,
    **kws,
):
    """Serialize to json."""
    if isinstance(obj, BaseJson):
        obj_data = obj.to_dict()
    else:
        obj_data = obj

    if fp is None:
        return json.dumps(obj_data, **kws)
    elif isinstance(fp, str):
        with open(fp, "w") as buffer:
            json.dump(obj_data, buffer, **kws)
        return None
    elif isinstance(fp, io.BufferedWriter):
        json.dump(obj_data, fp, **kws)
        return None
    else:
        raise TypeError(f"Invalid type {type(fp)}")


def dumps(obj: Union[BaseJson, TJsonTypes], **kws):
    """Serialize to string."""
    kws["fp"] = None
    return dump(obj, **kws)
