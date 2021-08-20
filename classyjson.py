""" General class objects for writing the parameters out. Does not have specific
logic for a particular parameters schema.
"""
# flake8: noqa: E501

# ############################################################################ #
# Imports
# ############################################################################ #

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
    import jsonschema

    _jsonschema_validate = jsonschema.validate
except ImportError:
    jsonschema = None
    _jsonschema_validate = lambda x: x


logger = logging.getLogger(__name__)


__all__ = [
    # dotdict
    "DotDict",
    # schema classes
    "StrSchema",
    "IntSchema",
    "NumberSchema",
    "BoolSchema",
    "NullSchema",
    "ObjectSchema",
    "ArraySchema",
    # classy json classes
    "ClassyJson",
    "ClassyObject",
    "ClassyArray",
    # load/dump functions
    "load",
    "loads",
    "dump",
    "dumps",
    # constants
    "JSON_TYPE_STR",
    "JSON_TYPE_NUMBER",
    "JSON_TYPE_INTEGER",
    "JSON_TYPE_OBJECT",
    "JSON_TYPE_ARRAY",
    "JSON_TYPE_BOOL",
    "JSON_TYPE_NULL",
]


JSON_TYPE_STR = "string"
JSON_TYPE_NUMBER = "number"
JSON_TYPE_INTEGER = "integer"
JSON_TYPE_OBJECT = "object"
JSON_TYPE_ARRAY = "array"
JSON_TYPE_BOOL = "boolean"
JSON_TYPE_NULL = "null"
# JSON_TYPE_DATETIME = "datetime"
ALL_JSON_TYPES = [
    JSON_TYPE_STR,
    JSON_TYPE_NUMBER,
    JSON_TYPE_INTEGER,
    JSON_TYPE_OBJECT,
    JSON_TYPE_ARRAY,
    JSON_TYPE_BOOL,
    JSON_TYPE_NULL,
]
# ############################################################################ #
# Types
# ############################################################################ #

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


# all json base types
TJson = Union[None, float, str, int, TJsonArray, TJsonObject]
# BaseSchema type
TBaseSchemaType = Type["BaseSchema"]
# ClassyJson type
TClassyJsonType = Type["ClassyJson"]


def _is_classy(obj: Any) -> bool:
    return isinstance(obj, type) and issubclass(obj, ClassyJson)


# ############################################################################ #
# DotDict
# ############################################################################ #


class DotDict(dict):
    """dot.notation access to dictionary keys"""

    # do you overwrite existing attributes? e.g. self.items or self.keys
    # if True then they are overwritten with the value
    _overwrite_attrs = False

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

    def _convert_value_type(self, value: VT) -> VT:
        # modify type on set
        value_type = type(value)
        if value_type == dict:  # pylint: disable=unidiomatic-typecheck
            return self._dictclass(value)
        elif isinstance(value, (list, tuple)):
            gen = map(self._convert_value_type, value)
            if isinstance(value, ClassyArray):
                return value.__class__(list(gen), validate=False)
            if value_type == list:
                return list(gen)
            if value_type == tuple:
                return tuple(gen)
            return value.__class__(gen)
        else:
            return value

    def _setitem_setattr(self, name: str, value: VT):
        if self._overwrite_attrs:
            self.__dict__[name] = value
        elif not hasattr(self, name):
            self.__dict__[name] = value

    def __setitem__(self, name: KT, value: VT):
        value_dotdict = self._convert_value_type(value)
        if isinstance(name, str):
            self._setitem_setattr(name, value_dotdict)
        return super().__setitem__(name, value_dotdict)

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

    def pop(self, key: KT, default: VT = None) -> VT:
        self.__dict__.pop(key, None)
        return super().pop(key, default)

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

    def __delattr__(self, name: str):
        """Use __delitem__"""
        return self.__delitem__(name)


# ############################################################################ #
# Schema Classes
# ############################################################################ #


def _get_jsonschema(schema: Union[TJson, TClassyJsonType, "BaseSchema"]) -> TJson:
    """Get the jsonschema"""
    if isinstance(schema, list):
        return [_get_jsonschema(value) for value in schema]
    if isinstance(schema, dict):
        return {key: _get_jsonschema(value) for key, value in schema.items()}
    if isinstance(schema, (float, str, int)):
        return schema
    raise TypeError(type(schema))  # pragma: no cover


class BaseSchema(dict):
    """Base jsonschema"""

    _schema_type: Union[str, list] = ""

    @property
    def schema_type(self) -> Union[str, list]:
        """Return the type"""
        return self["type"]

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

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def __add__(self, other):
        self_types = (
            self.schema_type
            if isinstance(self.schema_type, list)
            else [self.schema_type]
        )
        other_types = (
            other.schema_type
            if isinstance(other.schema_type, list)
            else [other.schema_type]
        )
        types = list(set(self_types + other_types))
        props = self.copy()
        props.update(other)
        props["type"] = types
        return BaseSchema(props)

    def __init__(self, schema: Dict[str, TJson] = None, **kws):
        schema_ = schema or {}
        for key, value in kws.items():
            if value is not None:
                schema_[key] = value
        schema_.setdefault("type", self._schema_type)
        super().__init__(**schema_)
        schema_type = self.schema_type
        if isinstance(schema_type, str):
            if schema_type not in ALL_JSON_TYPES:
                raise LookupError(
                    f"Unknown json type '{schema_type}' not in {ALL_JSON_TYPES}"
                )
        elif isinstance(schema_type, list):
            unknown_types = set(schema_type) - set(ALL_JSON_TYPES)
            if len(unknown_types):
                raise LookupError(
                    f"Unknown json types '{unknown_types}' not in {ALL_JSON_TYPES}"
                )
        else:
            raise TypeError(f"Unknown schema_type {type(schema_type)}")


class StrSchema(BaseSchema):
    """type=string

    https://json-schema.org/understanding-json-schema/reference/string.html
    """

    _schema_type: str = JSON_TYPE_STR

    def __init__(  # pylint: disable=too-many-arguments
        self,
        schema: Dict[str, TJson] = None,
        minLength: int = None,
        maxLength: int = None,
        pattern: str = None,
        format: str = None,  # pylint: disable=redefined-builtin
        **kws,
    ):
        """String json type

        Parameters
        ----------
        schema: can provide entire schema
        maxLength: The length of a string can be constrained using the minLength and maxLength keywords.
        minLength: The length of a string can be constrained using the minLength and maxLength keywords.
        pattern: The pattern keyword is used to restrict a string to a particular regular expression.
        format: The format keyword allows for basic semantic identification of certain kinds of string values that are commonly used.
        **kws: any other keywords
        """
        super().__init__(
            # as argument
            schema=schema,
            # specific
            minLength=minLength,
            maxLength=maxLength,
            pattern=pattern,
            format=format,
            # any other
            **kws,
        )


class NumberSchema(BaseSchema):
    """type=number

    https://json-schema.org/understanding-json-schema/reference/numeric.html
    """

    _schema_type: str = JSON_TYPE_NUMBER

    def __init__(  # pylint: disable=too-many-arguments
        self,
        schema: Dict[str, TJson] = None,
        multipleOf: int = None,
        minimum: float = None,
        exclusiveMinimum: Union[float, bool] = None,
        maximum: float = None,
        exclusiveMaximum: Union[float, bool] = None,
        **kws,
    ):
        """Number json type

        Parameters
        ----------
        schema: can provide entire schema
        multipleOf: Numbers can be restricted to a multiple of a given number, using the multipleOf keyword.
        minimum: Range for numbers.
        exclusiveMinimum: Range for numbers.
        maximum: Range for numbers.
        exclusiveMaximum: Range for numbers.
        **kws: any other keywords
        """
        super().__init__(
            # as argument
            schema=schema,
            # specific
            multipleOf=multipleOf,
            minimum=minimum,
            exclusiveMinimum=exclusiveMinimum,
            maximum=maximum,
            exclusiveMaximum=exclusiveMaximum,
            # any other
            **kws,
        )


class IntSchema(BaseSchema):
    """type=int

    https://json-schema.org/understanding-json-schema/reference/numeric.html
    """

    _schema_type: str = JSON_TYPE_INTEGER


class BoolSchema(BaseSchema):
    """type=bool

    https://json-schema.org/understanding-json-schema/reference/boolean.html
    """

    _schema_type: str = JSON_TYPE_BOOL


class NullSchema(BaseSchema):
    """type=null

    https://json-schema.org/understanding-json-schema/reference/null.html
    """

    _schema_type: str = JSON_TYPE_NULL


class ObjectSchema(BaseSchema):
    """Object json schema

    https://json-schema.org/understanding-json-schema/reference/object.html
    """

    _schema_type: str = JSON_TYPE_OBJECT

    def get_jsonschema(self) -> TJson:
        """Generate the full jsonschema"""
        schema = self.copy()
        if self.schema_properties:
            properties = {}
            for key, prop in self.schema_properties.items():
                if isinstance(prop, BaseSchema):
                    prop_schema = prop.get_jsonschema()
                elif _is_classy(prop):
                    prop_schema = prop.schema.get_jsonschema()
                else:
                    prop_schema = prop
                properties[key] = prop_schema
            schema["properties"] = properties
        return schema

    @property
    def schema_properties(self) -> Optional[Dict[str, TJson]]:
        """properties"""
        return self.get("properties")

    @property
    def schema_additional_properties(self) -> Optional[bool]:
        """additionalProperties"""
        return self.get("additionalProperties")

    @staticmethod
    def _load_prop(
        property_schema: Union[TJsonObject, TClassyJsonType], value: TJson = None
    ) -> Union[TJson, "ClassyJson"]:
        if value is None:
            return None

        if isinstance(property_schema, type) and issubclass(
            property_schema, ClassyJson
        ):
            classy = property_schema
            return classy(value, validate=False)

        return value

    def _load_known_properties(self, instance: TJson) -> Dict:
        properties = self.schema_properties or {}

        data = {}
        for key, prop_schema in properties.items():
            if key in instance:
                data[key] = self._load_prop(prop_schema, instance[key])
            elif "default" in prop_schema:
                default = prop_schema["default"]
                if isinstance(default, type) and issubclass(default, ClassyJson):
                    value = default()
                else:
                    value = default
                data[key] = value
        return data

    def _load_additional_properties(self, instance: TJson) -> Dict:
        properties = self.schema_properties or {}

        if self.schema_additional_properties is None:
            additional_properties = self.schema_properties is None
        else:
            additional_properties = self.schema_additional_properties

        data = {}
        if additional_properties:
            for key in instance:
                if key not in properties:
                    data[key] = self._load_prop(None, instance[key])
        return data

    # TODO: fix overload types so ObjectSchema return TJsonObject
    def load(self, instance: TJson, validate: bool = True) -> Any:
        """Load object"""
        instance = super().load(instance, validate=validate)
        if not isinstance(instance, dict):
            raise TypeError(f"Wrong instance base type: {type(instance)}")

        data = self._load_known_properties(instance)
        data.update(self._load_additional_properties(instance))
        return data

    def __init__(  # pylint: disable=too-many-arguments
        self,
        schema: Dict[str, TJson] = None,
        properties: Dict[str, TJson] = None,
        patternProperties: Dict[str, str] = None,
        required: List[str] = None,
        propertyNames: str = None,
        minProperties: int = None,
        maxProperties: int = None,
        additionalProperties: bool = None,
        **kws,
    ):
        """Object json type

        Parameters
        ----------
        schema: can provide entire schema
        properties:
        patternProperties:
        required:
        propertyNames:
        minProperties:
        maxProperties:
        additionalProperties:
        **kws: any other keywords
        """
        super().__init__(
            # as argument
            schema=schema,
            # specific
            properties=properties,
            patternProperties=patternProperties,
            required=required,
            propertyNames=propertyNames,
            minProperties=minProperties,
            maxProperties=maxProperties,
            additionalProperties=additionalProperties,
            # any other
            **kws,
        )


class ArraySchema(BaseSchema):
    """Schema Array Type

    https://json-schema.org/understanding-json-schema/reference/array.html
    """

    _schema_type: str = JSON_TYPE_ARRAY

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
            if schema_item is None:
                items.append(inst)
            else:
                item_type = schema_item["type"]
                if isinstance(item_type, type) and issubclass(item_type, ClassyJson):
                    classy = item_type
                    value = classy(inst, validate=False)
                    items.append(value)
                else:
                    items.append(inst)
        return items

    def __init__(
        self,
        schema: Dict[str, TJson] = None,
        items: Union[TJsonObject, TJsonArray] = None,
        additionalItems: bool = None,
        contains: Dict[str, str] = None,
        minItems: int = None,
        maxItems: int = None,
        uniqueItems: bool = None,
        **kws,
    ):
        """Array type

        Parameters
        ----------
        schema: can provide entire schema
        items: List or Tuple validation.
        additionalItems:
            The additionalItems keyword controls whether it’s valid to have
            additional items in a tuple beyond what is defined in items.
        contains:
            While the items schema must be valid for every item in the array,
            the contains schema only needs to validate against one or more
            items in the array.
        minItems: The length of the array.
        maxItems: The length of the array.
        uniqueItems: Each of the items in an array is unique.
        **kws: any other keywords
        """
        super().__init__(
            # as argument
            schema=schema,
            # specific
            items=items,
            additionalItems=additionalItems,
            contains=contains,
            minItems=minItems,
            maxItems=maxItems,
            uniqueItems=uniqueItems,
            # any other
            **kws,
        )


# ############################################################################ #
# Classy Classes
# ############################################################################ #


class ClassyJson:  # pylint: disable=too-few-public-methods
    """Python JSON Schema class object"""

    _schema_class: TBaseSchemaType = BaseSchema
    _schema_raw: Dict[str, Union[TJson, TClassyJsonType]] = {}
    schema: BaseSchema

    def __init_subclass__(cls) -> None:
        schema_class = cls._schema_class

        schema = getattr(cls, "schema", {}) or {}
        if not isinstance(schema, BaseSchema):
            cls._schema_raw = schema.copy()
            cls.schema = schema_class(**schema)

    def __init__(self):
        """self, instance: TJson, validate: bool = True"""
        if not isinstance(self.schema, BaseSchema):
            self.schema = self._schema_class(self.schema)

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"


class ClassyObject(ClassyJson, DotDict):
    """Json Schema type 'object'"""

    _schema_class: TBaseSchemaType = ObjectSchema

    def __init__(self, instance: TJson = None, validate: bool = True):
        super().__init__()
        self._dictclass = DotDict
        data = self.schema.load(instance or {}, validate=validate)
        self.update(data)

    def __repr__(self):
        return f"{self.__class__.__name__}({dict.__repr__(self)})"


class ClassyArray(ClassyJson, list):
    """Json Schema type 'array'"""

    _schema_class: TBaseSchemaType = ArraySchema

    def __init__(self, instance: TJson = None, validate: bool = True):
        super().__init__()
        items = self.schema.load(instance or [], validate=validate)
        self.extend(items)

    def __repr__(self):
        return f"{self.__class__.__name__}({list.__repr__(self)})"


# ############################################################################ #
# load/dump functions
# ############################################################################ #


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
    classy: TClassyJsonType = None,
    classy_options: Tuple[str, Dict[str, TClassyJsonType]] = None,
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
    classy: TClassyJsonType = None,
    classy_options: Tuple[str, Dict[str, TClassyJsonType]] = None,
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
