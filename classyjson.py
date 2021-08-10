""" General class objects for writing the parameters out. Does not have specific
logic for a particular parameters schema.
"""
# flake8: noqa: E501
# standard
import logging
from typing import (  # pylint: disable=no-name-in-module
    Any,
    Tuple,
    Dict,
    List,
    Union,
    Optional,
    Type,
    TypeVar,
    IO,
    Protocol,
)
import json
import io
import os

# external
try:
    from jsonschema import validate as _jsonschema_validate
except ImportError:
    _jsonschema_validate = lambda x: x


logger = logging.getLogger(__name__)


__all__ = [
    "ClassyJson",
    "ClassyObject",
    "ClassyArray",
    "load",
    "loads",
    "dump",
    "dumps",
    # types
    "TClassyJson",
    "TJson",
    "JSON_TYPE_STR",
    "JSON_TYPE_NUMBER",
    "JSON_TYPE_INTEGER",
    "JSON_TYPE_OBJECT",
    "JSON_TYPE_ARRAY",
    "JSON_TYPE_BOOL",
    "JSON_TYPE_NULL",
    "JSON_TYPE_DATETIME",
]


JSON_TYPE_STR = "string"
JSON_TYPE_NUMBER = "number"
JSON_TYPE_INTEGER = "integer"
JSON_TYPE_OBJECT = "object"
JSON_TYPE_ARRAY = "array"
JSON_TYPE_BOOL = "boolean"
JSON_TYPE_NULL = "null"
JSON_TYPE_DATETIME = "datetime"


# typing

KT = TypeVar("KT")
VT = TypeVar("VT")


class TJsonArray(Protocol):
    """JSON Array Type
    https://github.com/python/typing/issues/182#issuecomment-893657366
    """

    __class__: Type[List["TJson"]]  # type: ignore


class TJsonObject(Protocol):
    """JSON Object Type
    https://github.com/python/typing/issues/182#issuecomment-893657366
    """

    __class__: Type[Dict[str, "TJson"]]  # type: ignore


TJson = Union[None, float, str, int, TJsonArray, TJsonObject]


TClassyJson = Type["ClassyJson"]


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

    def __setitem__(self, name: KT, value: VT):
        # modify type on set
        if type(value) == dict:  # pylint: disable=unidiomatic-typecheck
            value_dotdict = self._dictclass(value)
        else:
            value_dotdict = value
        if isinstance(name, str):
            self.__dict__[name] = value_dotdict
        return super().__setitem__(name, value)

    def setdefault(self, key: KT, default: VT = None) -> VT:
        """Set default"""
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


def _get_jsonschema(schema: Union[TJson, TClassyJson, "BaseSchema"]) -> TJson:
    """Get the jsonschema"""
    if isinstance(schema, list):
        return [_get_jsonschema(value) for value in schema]
    if isinstance(schema, dict):
        return {key: _get_jsonschema(value) for key, value in schema.items()}
    if schema is None:
        return None
    if isinstance(schema, (float, str, int)):
        return schema
    if isinstance(schema, BaseSchema):
        return schema.get_jsonschema()
    if isinstance(schema, type) and issubclass(schema, ClassyJson):
        return schema.schema.get_jsonschema()
    raise TypeError(type(schema))


class BaseSchema(dict):
    """Base jsonschema"""

    schema_type: str = ""

    def get_jsonschema(self) -> TJson:
        """Get the jsonschema for this"""
        return _get_jsonschema(dict(self))

    def validate(self, instance: TJson, **kws):
        """Validate instance against schema"""
        _jsonschema_validate(instance, self.get_jsonschema(), **kws)

    def load(self, instance: TJson, validate: bool = True) -> Any:
        """Parse into objects"""
        if validate:
            self.validate(instance)
        return instance


TBaseSchemaType = Type[BaseSchema]


class ObjectSchema(BaseSchema):
    """Object json schema"""

    schema_type: str = JSON_TYPE_OBJECT

    def get_jsonschema(self) -> TJson:
        """Generate the full jsonschema"""
        schema = self.copy()
        properties = {}
        schema_properties = schema.get("properties", {})
        for key, prop in schema_properties.items():
            if isinstance(prop, BaseSchema):
                prop_schema = prop.get_jsonschema()
            elif _is_classy(prop):
                prop_schema = prop.schema.get_jsonschema()
            else:
                prop_schema = prop
            properties[key] = prop_schema
        schema["properties"] = properties
        return schema

    @staticmethod
    def _load_prop(
        property_schema: dict, value: TJson = None
    ) -> Union[TJson, TClassyJson]:
        if value is None:
            if isinstance(property_schema, dict):
                if "default" in property_schema:
                    default = property_schema["default"]
                    if _is_classy(default):
                        return default()
                    return default
                return None
            return None

        if _is_classy(property_schema):
            classy = property_schema
            return classy(value, validate=False)

        return value

    # TODO: fix overload types so ObjectSchema can be TJsonObject
    def load(self, instance: TJson, validate: bool = True) -> Any:
        """ Load object """
        instance = super().load(instance, validate=validate)
        if not isinstance(instance, dict):
            raise TypeError(f"Wrong instance base type: {type(instance)}")

        props = self.get("properties", {})
        data = {}
        for prop_key, prop_schema in props.items():
            value = None
            if prop_key in instance:
                value = instance[prop_key]
            data[prop_key] = self._load_prop(prop_schema, value)

        return data

    def __init__(self, properties=None, **kws):
        kws.update(
            type=self.schema_type,
            properties=properties,
        )
        super().__init__(**kws)


class ArraySchema(BaseSchema):
    """Schema Array Type"""

    schema_type: str = JSON_TYPE_ARRAY

    def get_jsonschema(self) -> TJson:
        """Get the jsonschema for this"""
        schema = self.copy()

        items = schema.get("items")
        if items is None:
            return schema
        elif isinstance(items, BaseSchema):
            schema["items"] = items.get_jsonschema()
        elif _is_classy(items):
            schema["items"] = items.schema.get_jsonschema()
        elif isinstance(items, list):
            items_schema = []
            for item in items:
                if isinstance(item, BaseSchema):
                    items_schema.append(item.get_jsonschema())
                elif _is_classy(item):
                    items_schema.append(item.schema.get_jsonschema)
                else:
                    items_schema.append(dict(item))
            schema["items"] = items_schema
        elif items is not None:
            schema["items"] = items
        return schema

    def load(self, instance: TJson, validate: bool = True) -> Any:
        """Parse into objects"""
        instance = super().load(instance, validate=validate)
        if not isinstance(instance, list):
            raise TypeError(f"Instance must be of base type list not {type(instance)}")

        def _inf_item_generator(item):
            """Return this item"""
            while True:
                yield item

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
            if isinstance(item_type, type) and issubclass(item_type, ClassyJson):
                classy = item_type
                value = classy(inst, validate=False)
                items.append(value)
            else:
                items.append(inst)
        return items

    def __init__(self, items: Union[TJsonObject, TJsonArray] = None, **kws):
        kws.update(
            type=self.schema_type,
            items=items,
        )
        super().__init__(**kws)


class ClassyJson:  # pylint: disable=too-few-public-methods
    """Python JSON Schema class object"""

    _schema_class: TBaseSchemaType = BaseSchema
    _schema_raw: Dict[str, Union[TJson, TClassyJson]] = {}
    schema: BaseSchema = BaseSchema({})

    def __init_subclass__(cls) -> None:
        schema_class = cls._schema_class
        if cls.schema is None:
            raise TypeError(f"Must define schema for {cls}")

        if not isinstance(cls.schema, BaseSchema):
            cls._schema_raw = cls.schema.copy()
            cls.schema = schema_class(**cls._schema_raw)

    def __init__(self, instance: TJson, validate: bool = True):
        if not isinstance(self.schema, BaseSchema):
            self.schema = self._schema_class(self.schema)
        self.schema.load(instance, validate=validate)

    def initialize(self):
        """Runs after init with different signature"""


def _is_classy(obj: Any) -> bool:
    return isinstance(obj, type) and issubclass(obj, ClassyJson)


class ClassyObject(ClassyJson, DotDict):
    """Json Schema type 'object' """

    _schema_class: TBaseSchemaType = ObjectSchema
    schema: BaseSchema = ObjectSchema({})

    def __init__(self, instance: TJson, validate: bool = True):
        super().__init__(instance, validate=validate)
        self._dictclass = DotDict
        data = self.schema.load(instance, validate=False)
        self.update(data)
        self.initialize()


class ClassyArray(ClassyJson, list):
    """Json Schema type 'array' """

    _schema_class: TBaseSchemaType = ArraySchema
    schema: ArraySchema = ArraySchema({})

    def __init__(self, instance: TJson, validate: bool = True):
        super().__init__(instance, validate=validate)
        items = self.schema.load(instance, validate=False)
        self.extend(items)
        self.initialize()


def _load_json(
    json_data: Union[str, Dict, IO[str]],
    **kws,
) -> TJson:
    """Wrapper around json.load which handles overloaded json types"""
    if isinstance(json_data, dict):
        return json_data

    if isinstance(json_data, str):
        if os.path.exists(json_data):
            with open(json_data) as buffer:
                json_loaded = json.load(buffer, **kws)
        else:
            json_loaded = json.loads(json_data, **kws)
        return json_loaded

    if isinstance(json_data, io.BufferedReader):
        return json.load(json_data, **kws)

    raise TypeError(f"Invalid type {type(json_data)}")


def load(
    json_data: Union[str, Dict, IO[str]],
    classy: TClassyJson = None,
    classy_options: Tuple[str, Dict[str, TClassyJson]] = None,
    **kws,
) -> Union[ClassyJson, TJson]:
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
    elif isinstance(classy, type):
        return classy(json_loaded)
    else:
        return classy.__class__(json_loaded)


def loads(
    json_data: str,
    classy: TClassyJson = None,
    classy_options: Tuple[str, Dict[str, TClassyJson]] = None,
) -> Union[ClassyJson, TJson]:
    """Load from string"""
    return load(
        json_data,
        classy=classy,
        classy_options=classy_options,
    )


def dump(
    obj: Union[ClassyJson, TJson],
    fp: Union[str, IO[str]] = None,
    **kws,
) -> Optional[str]:
    """Serialize to json."""
    if fp is None:
        return json.dumps(obj, **kws)

    if isinstance(fp, str):
        with open(fp, "w") as buffer:
            json.dump(obj, buffer, **kws)
        return None

    if isinstance(fp, io.BufferedWriter):
        json.dump(obj, fp, **kws)
        return None

    raise TypeError(f"Invalid type {type(fp)}")


def dumps(obj: Union[ClassyJson, TJson], **kws) -> Optional[str]:
    """Serialize to string."""
    kws["fp"] = None
    return dump(obj, **kws)
