""" General class objects for writing the parameters out. Does not have specific
logic for a particular parameters schema.
"""
# flake8: noqa: E501
# standard
import logging
from typing import Any, Tuple, Dict, List, Union, KT, VT
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


class BaseSchema(dict):
    """Base jsonschema"""

    schema_type = None

    def get_jsonschema(self):
        """Get the jsonschema for this"""
        data = {}
        for key, value in self.items():
            if isinstance(value, type) and issubclass(value, BaseJson):
                value_jsonschema = value.schema.get_jsonschema()
            elif isinstance(value, BaseSchema):
                value_jsonschema = value.get_jsonschema()
            else:
                value_jsonschema = value
            data[key] = value_jsonschema
        return data

    def validate(self, instance: TJsonTypes, **kws):
        """Validate instance against schema"""
        jsonschema.validate(instance, self.get_jsonschema(), **kws)

    def load(self, instance: Dict[str, Any], validate: bool = True) -> Dict:
        """Parse into objects"""
        if validate:
            self.validate(instance)
        return instance


class ObjectSchema(BaseSchema):
    """Object json schema"""

    schema_type = JSON_TYPE_OBJECT

    def get_jsonschema(self) -> dict:
        """Generate the full jsonschema"""
        schema = self.copy()
        properties = {}
        schema_properties = schema.get("properties", {})
        for key, prop in schema_properties.items():
            if isinstance(prop, type) and issubclass(prop, BaseSchema):
                prop_schema = prop.get_jsonschema()
            if isinstance(prop, type) and issubclass(prop, BaseJson):
                prop_schema = prop.schema.get_jsonschema()
            else:
                prop_schema = prop
            properties[key] = prop_schema
        schema["properties"] = properties
        return schema

    def load(self, instance: Dict[str, Any], validate: bool = True) -> Dict:
        """ Load object """
        instance = super().load(instance, validate=validate)
        if not isinstance(instance, dict):
            raise TypeError(f"Wrong instance base type: {type(instance)}")

        props = self.get("properties", {})
        data = {}
        for prop_key, prop_schema in props.items():
            if prop_key not in instance:
                if isinstance(prop_schema, type) and issubclass(
                    prop_schema, BaseSchema
                ):
                    value = prop_schema()
                elif isinstance(prop_schema, dict):
                    if "default" in prop_schema:
                        default = prop_schema["default"]
                        if isinstance(default, type) and issubclass(
                            default, BaseSchema
                        ):
                            value = default()
                        else:
                            value = default
                else:
                    value = None
                data[prop_key] = value
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

    def __init__(self, properties=None, **kws):
        kws.update(
            type=self.schema_type,
            properties=properties,
        )
        super().__init__(**kws)


class ArraySchema(BaseSchema):
    """Schema Array Type"""

    schema_type = JSON_TYPE_ARRAY

    def get_jsonschema(self) -> dict:
        """Get the jsonschema for this"""
        schema = self.copy()

        items = schema.get("items")
        if isinstance(items, type) and issubclass(items, BaseSchema):
            schema["items"] = items.get_jsonschema()
        elif isinstance(items, type) and issubclass(items, BaseJson):
            schema["items"] = items.schema.get_jsonschema()
        elif isinstance(items, list):
            items_schema = []
            for item in items:
                if isinstance(item, type) and issubclass(item, BaseSchema):
                    items_schema.append(item.get_jsonschema)
                else:
                    items_schema.append(dict(item))
            schema["items"] = items_schema
        elif items is not None:
            schema["items"] = items
        return schema

    def load(self, instance, validate=True) -> List:
        """Parse into objects"""
        instance = super().load(instance, validate=validate)
        if not isinstance(instance, list):
            raise TypeError(f"Instance must be of base type list not {type(instance)}")

        schema_items = self.get("items", None)

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

    def __init__(self, items=None, **kws):
        kws.update(
            type=self.schema_type,
            items=items,
        )
        super().__init__(**kws)


class MetaBaseJson(type):
    """Metadata class for checking the schema on the class"""

    def __init__(cls, name, bases, dict_):
        schema_class = cls._schema_class
        cls._raw_schema = cls.schema.copy()
        cls.schema = schema_class(**cls._raw_schema)
        super().__init__(name, bases, dict_)


class BaseJson(metaclass=MetaBaseJson):  # pylint: disable=too-few-public-methods
    """Python JSON Schema class object"""

    _schema_class: type = BaseSchema
    schema: BaseSchema = {}

    def __init__(self, instance: Dict[str, Any], validate: bool = True):
        if not isinstance(self.schema, BaseSchema):
            self.schema = self._schema_class(self.schema)
        self.schema.load(instance, validate=validate)
        self.initialize()

    def initialize(self):
        """Runs after init with different signature"""


class ObjectJson(BaseJson, DotDict):
    """Json Schema type 'object' """

    _schema_class: type = ObjectSchema
    schema: ObjectSchema = {}

    def __init__(self, instance: Dict[str, Any], validate: bool = True):
        super().__init__(instance, validate=validate)
        self._dictclass = DotDict
        data = self.schema.load(instance, validate=False)
        self.update(data)
        self.initialize()


class ArrayJson(BaseJson, list):
    """Json Schema type 'array' """

    _schema_class = ArraySchema
    schema: ArraySchema = {}

    def __init__(self, instance: TJsonTypes, validate: bool = True):
        super().__init__(instance, validate=validate)
        items = self.schema.load(instance, validate=False)
        self.extend(items)
        self.initialize()


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
        if not isinstance(json_loaded, dict):
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
