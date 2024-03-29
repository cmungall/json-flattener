"""
Procedures for flattening and unflattening dicts to tables.

See README.md for full details
"""

import csv
import json
import logging
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Dict, List, Optional, Set, TextIO, Tuple, Union

import yaml

DEFAULT_LIST_PARENS = ("[", "]")
KEYNAME = str
ATOM = Union[str, int, float]
CELL_VALUE = Union[ATOM, List[ATOM]]
ROW = Dict[KEYNAME, CELL_VALUE]
OBJECT = Dict[KEYNAME, Any]


class MissingColumnError(ValueError):
    """Exception raised when a column is missing from a row."""

    def __init__(self, row: ROW, value: Any):
        """Initialize exception."""
        super().__init__(f"Value {value} has no column row {row}")


@unique
class Serializer(Enum):
    """Vocabulary of methods to use for serialization objects."""

    yaml = "yaml"
    json = "json"
    pickle = "pickle"
    as_str = "as_str"

    @staticmethod
    def list():
        """List all elements in enum."""
        return list(map(lambda c: c.value, Serializer))


@dataclass
class ConfigEntity:
    """Base class for configurations."""

    def as_dict(self) -> dict:
        """
        Serialize as a dictionary.

        :return:
        """
        def _convert(o: Any) -> Any:
            if isinstance(o, ConfigEntity):
                return o.as_dict()
            elif isinstance(o, dict):
                return {k: _convert(v) for k, v in o.items()}
            elif isinstance(o, list) or isinstance(o, tuple):
                return [_convert(v) for v in o]
            elif isinstance(o, Enum):
                return o.value
            else:
                return o

        return {k: _convert(v) for k, v in self.__dict__.items()}


@dataclass
class KeyConfig(ConfigEntity):
    """Configures the behavior of an individual key/column."""

    delete: bool = False
    """for nested columns, if denormalized into other columns"""

    serializers: List[Serializer] = None
    """all serializers to apply"""

    flatten: bool = False
    """Flatten this field"""

    is_list: bool = False
    """The value of the field is a python list or collection"""

    melt_list_elements: bool = False
    """Not yet implemented"""

    distinct_values: Set[Any] = None
    """All distinct values (unused)"""

    mappings: Dict[KEYNAME, KEYNAME] = None
    """maps normalized keys to denormalized"""

    typemap: Dict[KEYNAME, str] = None
    """Mapping of types"""

    def __post_init__(self):
        if self.serializers is None:
            self.serializers = []
        if self.serializers is not None:
            if not isinstance(self.serializers, List):
                self.serializers = [self.serializers]
            self.serializers = [
                Serializer(x) if isinstance(x, str) else x
                for x in self.serializers
            ]
        if self.mappings is None:
            self.mappings = {}

    @staticmethod
    def from_dict(**obj: Dict[str, Any]):
        """
        Create object from a dictionary.

        :param obj:
        :return:
        """
        nu = KeyConfig(**obj)
        nu.serializers = [Serializer(s) for s in nu.serializers]
        return nu

    def _type_map(self):
        return {"serializers": Serializer}


@dataclass
class GlobalConfig(ConfigEntity):
    """Configuration for a multi-key object."""

    key_configs: Dict[KEYNAME, KeyConfig] = None
    sep: str = field(default_factory=lambda: "_")
    csv_delimiter: str = field(default_factory=lambda: "\t")
    csv_inner_delimiter: str = field(default_factory=lambda: "|")
    csv_list_markers: Tuple[str, str] = field(
        default_factory=lambda: DEFAULT_LIST_PARENS
    )
    strict: bool = field(default_factory=lambda: True)

    def __post_init__(self):
        if self.key_configs is None:
            self.key_configs = {}
        # for k, v in self.key_configs.items():
        #    self.key_configs[k] = KeyConfig(v)

    @staticmethod
    def from_dict(**obj: Dict[str, Any]):
        """
        Create an object from a dictionary.

        :param obj:
        :return:
        """
        nu = GlobalConfig(**obj)
        for k, v in nu.key_configs.items():
            nu.key_configs[k] = KeyConfig.from_dict(**v)
        return nu

    def _type_map(self):
        return {"key_configs": KeyConfig}


CONFIGMAP = Dict[KEYNAME, KeyConfig]


def _serialized_field_name(
    field: KEYNAME, sep: str, serializer: Serializer
) -> str:
    return f"{field}{sep}{serializer.name}"


def flatten(
    objs: List[OBJECT], config: GlobalConfig = GlobalConfig()
) -> List[ROW]:
    """
    Flattens a list of dicts into a denormalized representation.

    :param objs: a list of dicts to be flattened
    :param config: mapping configuration
    :raises NotImplementedError:
    :return: list of flattened dicts
    """
    sep = config.sep
    configmap = config.key_configs
    objs2 = [obj.copy() for obj in objs]
    # outer loop is based on keys, with inner loops for object lists, this is more efficient
    for field_name, config in configmap.items():
        field_map = config.mappings
        # Serializers: some fields may be serialized as json/yaml blobs
        serializers = config.serializers
        for serializer in serializers:
            # typically a field `foo` holding an object will be mapped to `foo_json` or `foo_yaml`
            injected_field = _serialized_field_name(field_name, sep, serializer)
            for obj in objs2:
                if field_name in obj:
                    if serializer == Serializer.yaml:
                        dumpstr = yaml.dump(obj[field_name])
                    elif serializer == Serializer.json:
                        dumpstr = json.dumps(obj[field_name])
                    elif serializer == Serializer.pickle:
                        import pickle

                        dumpstr = pickle.dumps(obj[field_name])
                    elif serializer == Serializer.as_str:
                        dumpstr = str(obj[field_name])
                    else:
                        raise NotImplementedError(f"unknown serializer: {serializer}")
                    obj[injected_field] = dumpstr
        if config.melt_list_elements:
            if config.distinct_values is None:
                config.distinct_values = set()
        # flattening non-list objects
        if config.flatten and not config.is_list:
            for obj in objs2:
                inner_obj = obj[field_name]
                if not isinstance(inner_obj, dict):
                    # inner object is assumed to be a complex object
                    raise Exception(
                        f"Value of {field_name} = {obj}, which is not a dict. Consider configuring {field_name} to be a list"
                    )
                for k, v in inner_obj.items():
                    # flatten inner object. TODO: recursively expand
                    injected_field = f"{field_name}{sep}{k}"
                    obj[injected_field] = v  # e.g. book_name = "..."
                    field_map[k] = injected_field
        # flattening lists of objects
        if config.flatten and config.is_list:
            for obj in objs2:
                inner_objs = obj.get(field_name, [])
                inner_fields = set()
                for inner_obj in inner_objs:
                    inner_fields.update(inner_obj.keys())
                injected_field_map: Dict[KEYNAME, KEYNAME] = {}
                for k in inner_fields:
                    injected_field_map[
                        k
                    ] = f"{field_name}{sep}{k}"  # e.g book_price
                    obj[injected_field_map[k]] = []
                for inner_obj in inner_objs:
                    for k, injected_field in injected_field_map.items():
                        v = inner_obj.get(k, None)
                        obj[injected_field].append(v)
                        if v is not None and config.melt_list_elements:
                            obj[v] = True
                        field_map[k] = injected_field
        if config.melt_list_elements and not (
            config.flatten and config.is_list
        ):
            for obj in objs2:
                inner_objs = obj.get(field_name, [])
                if config.melt_list_elements:
                    config.distinct_values.update(inner_objs)
                for inner_obj in inner_objs:
                    if config.melt_list_elements:
                        obj[inner_obj] = True
        if config.delete:
            for obj in objs2:
                if field_name in obj:
                    del obj[field_name]
    return objs2


def unflatten(
    objs: List[ROW], config: GlobalConfig = GlobalConfig(), **params
) -> List[OBJECT]:
    """
    Reverses the flatten operation

    :param objs: list of dicts to be unflattened
    :param config:
    :param params:
    :raises NotImplementedError:
    :return:
    """
    sep = config.sep
    configmap = config.key_configs
    objs2 = [obj.copy() for obj in objs]
    for field, config in configmap.items():
        field_map = config.mappings
        serializers = config.serializers
        # unflatten from fields foo_json ==> foo
        for serializer in serializers:
            injected_field = _serialized_field_name(field, sep, serializer)
            for obj in objs2:
                if injected_field in obj:
                    serialized_v = obj[injected_field]
                    if serialized_v is not None:
                        if serializer == Serializer.yaml:
                            nu_obj = yaml.safe_load(serialized_v)
                        elif serializer == Serializer.json:
                            nu_obj = json.loads(serialized_v)
                        elif serializer == Serializer.pickle:
                            import pickle

                            nu_obj = pickle.loads(serialized_v)
                        else:
                            raise NotImplementedError(f"unknown serializer: {serializer}")
                        obj[field] = nu_obj
                    del obj[injected_field]
                else:
                    logging.error(f"Expected: {injected_field} in {obj}")
        # non-list objects: unflatten foo_bar == "..." --> foo.bar
        if config.flatten and not config.is_list:
            for obj in objs2:
                inner_obj = {}
                logging.info(f"field={field}, obj={obj} using fmap={field_map}")
                for k, injected_field in field_map.items():
                    if injected_field in obj:
                        inner_obj[k] = obj[injected_field]
                        del obj[injected_field]
                if field not in obj:
                    obj[field] = inner_obj
        # list objects: unflatten foo_bar == [...] --> foo = [bar1, ...]
        if config.flatten and config.is_list:
            logging.info(f"field_map = {field_map}")
            for obj in objs2:
                # ignore null values or empty lists
                fmap_actual = {
                    k: injected_field
                    for k, injected_field in field_map.items()
                    if injected_field in obj
                    and obj[injected_field] is not None
                    and len(obj[injected_field]) > 0
                }
                if len(fmap_actual.values()) > 0:
                    injected_field = list(fmap_actual.values())[
                        0
                    ]  # pick arbitrary
                    inner_objs = [
                        {} for x in obj[injected_field]
                    ]  # seed inner objects
                    for i in range(0, len(inner_objs)):
                        inner_obj = inner_objs[i]
                        for k, injected_field in fmap_actual.items():
                            if obj[injected_field][i] is not None:
                                inner_obj[k] = obj[injected_field][i]
                    if field not in obj:
                        obj[field] = inner_objs
                for injected_field in field_map.values():
                    if injected_field in obj:
                        del obj[injected_field]
    return objs2


def flatten_to_csv(
    objs: List[OBJECT],
    outstream,
    config: GlobalConfig = None,
    **params,
):
    """
    Serialize a list of objects as a CSV

    :param objs:
    :param config:
    :param params:
    :return:
    """
    if config is None:
        config = GlobalConfig()
    delimiter = config.csv_delimiter
    internal_delimiter = config.csv_inner_delimiter
    list_parens = config.csv_list_markers
    internal_delimiter_esc = f"\\{internal_delimiter}"
    lo, lc = list_parens

    def _serialize_as_str(x: Optional[Any]) -> str:
        if x is None:
            return ""
        else:
            return str(x).replace(internal_delimiter, internal_delimiter_esc)

    flat_objs = flatten(objs, config, **params)
    fieldnames = []
    for obj in flat_objs:
        for k in obj.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    w = csv.DictWriter(
        outstream,
        delimiter=delimiter,
        fieldnames=fieldnames,
        quoting=csv.QUOTE_NONE,
        escapechar="\\",
        lineterminator="\n",
    )
    w.writeheader()
    for obj in flat_objs:
        nu_obj = {}
        for k, v in obj.items():
            if isinstance(v, list):
                v = internal_delimiter.join([_serialize_as_str(x) for x in v])
                v = f"{lo}{v}{lc}"
            else:
                v = _serialize_as_str(v)
            nu_obj[k] = v
        w.writerow(nu_obj)


def unflatten_from_csv(
    source: TextIO, config: GlobalConfig = GlobalConfig(), **params
) -> List[OBJECT]:
    """
    Read serialized objects from a CSV file

    :param source: file-like object
    :param config:
    :param params:
    :return:
    """
    delimiter = config.csv_delimiter
    internal_delimiter = config.csv_inner_delimiter
    list_parens = config.csv_list_markers
    if isinstance(source, str):
        instream = open(source)
    else:
        instream = source
    r = csv.DictReader(
        instream, delimiter=delimiter, quoting=csv.QUOTE_NONE, escapechar="\\"
    )
    lo, lc = list_parens

    def _getval(x: str) -> Optional[Any]:
        if x == "":
            return None
        else:
            try:
                return int(x)
            except ValueError:
                try:
                    return float(x)
                except ValueError:
                    return x

    # check which fields are serialized
    serialized_fields = set()
    gconfig = config.key_configs
    for field, kconfig in gconfig.items():
        serializers = kconfig.serializers
        for serializer in serializers:
            injected_field = _serialized_field_name(
                field, config.sep, serializer
            )
            serialized_fields.add(injected_field)

    objs = []
    for row in r:
        nu_obj = {}
        for k, v in row.items():
            if k is None:
                raise MissingColumnError(row, v)
            key_config = config.key_configs.get(k, None)
            v = v.replace("\\n", "\n").replace("\\t", "\t")
            # lists are demarcated by list markers
            is_direct_list = False
            if key_config is not None and key_config.is_list:
                is_direct_list = True
            if not is_direct_list:
                if (
                    lo != ""
                    and lc != ""
                    and v.startswith(lo)
                    and v.endswith(lc)
                ):
                    is_direct_list = True
            if k in serialized_fields:
                is_direct_list = False
            # if (lo != '' or lc != '') and v.startswith(lo) and v.endswith(lc) and not k.endswith('_json') and not k.endswith('_yaml'):
            if is_direct_list:
                if lo != "":
                    if v.startswith(lo):
                        v = v.replace(lo, "", 1)
                    else:
                        raise Exception(
                            f"Expected start-of-list marker {lo} in {k}={v}"
                        )
                if lc != "":
                    if v.endswith(lc):
                        v = v[0 : -len(lc)]
                    else:
                        raise Exception(
                            f"Expected end-of-list marker {lc} in {k}={v}"
                        )
                # TODO: escaping
                v = [_getval(x) for x in v.split(internal_delimiter)]
            else:
                v = _getval(v)
            if v is not None:
                nu_obj[k] = v
        objs.append(nu_obj)
    return unflatten(objs, config, **params)
