"""
json_denormalizer

See also:

 - https://pandas.pydata.org/pandas-docs/version/0.25.0/reference/api/pandas.io.json.json_normalize.html


 https://github.com/wnameless/json-flattener

"""
from dataclasses import dataclass
from enum import Enum, unique
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import yaml
import json
import pickle
import logging
import json
import csv

DEFAULT_LIST_PARENS = ('[', ']')

KEYNAME = str

@unique
class Serializer(Enum):
    yaml = 'yaml'
    json = 'json'
    pickle = 'pickle'
    as_str = 'as_str'
    @staticmethod
    def list():
        return list(map(lambda c: c.value, Serializer))



@dataclass
class KeyConfig:
    """
    Configures the flattening/unflattening behavior of an individual key
    """
    delete: bool = False
    serializers: List[Serializer] = None
    flatten: bool = False
    is_list: bool = False
    melt_list_elements: bool = False  ## not implemented yet
    mappings: Dict[KEYNAME, KEYNAME] = None
    typemap: Dict[KEYNAME, str] = None

    def __post_init__(self):
        if self.serializers is None:
            self.serializers = []
        if self.serializers is not None:
            if not isinstance(self.serializers, List):
                self.serializers = [self.serializers]
            self.serializers = [Serializer(x) if isinstance(x, str) else x for x in self.serializers]
        if len(self.serializers) == 0:
            if not self.flatten:
                raise Exception(f'Must set EITHER flatten OR serializers')
        if self.mappings is None:
            self.mappings = {}

@dataclass
class GlobalConfig:
    key_configs: Dict[KEYNAME, KeyConfig] = None
    sep: str = '_'
    csv_delimiter: str = '\t'
    csv_inner_delimiter: str = '|'
    csv_list_quotes: Tuple[str, str] = ('[', ']')
    strict = True

CONFIGMAP = Dict[KEYNAME,KeyConfig]


def _serialized_field_name(field: KEYNAME, sep: str, serializer: Serializer) -> str:
    return f'{field}{sep}{serializer.name}'

def flatten(objs: List[dict], config: GlobalConfig = GlobalConfig()) -> List:
    """
    Flattens a list of dicts into a denormalized representation according to a configuration

    :param objs: a list of dicts to be flattened
    :param configmap: mapping between outer keys in the above list to a configuration for mapping
    :param sep: separator used for flattened fields
    :return: list of flattened dicts
    """
    sep = config.sep
    configmap = config.key_configs
    objs2 = [obj.copy() for obj in objs]
    for field, config in configmap.items():
        fmap = config.mappings
        serializers = config.serializers
        for serializer in serializers:
            f2 = _serialized_field_name(field, sep, serializer)
            for obj in objs2:
                if field in obj:
                    if serializer == Serializer.yaml:
                        dumpstr = yaml.dump(obj[field])
                    elif serializer == Serializer.json:
                        dumpstr = json.dumps(obj[field])
                    elif serializer == Serializer.pickle:
                        dumpstr = pickle.dumps(obj[field])
                    elif serializer == Serializer.as_str:
                        dumpstr = str(obj[field])
                    else:
                        raise Exception(f'unknown serializer: {serializer}')
                    obj[f2] = dumpstr
        if config.flatten and not config.is_list:
            for obj in objs2:
                inner_obj = obj[field]
                for k, v in inner_obj.items():
                    f2 = f'{field}{sep}{k}'
                    obj[f2] = v
                    fmap[k] = f2
        if config.flatten and config.is_list:
            for obj in objs2:
                inner_objs = obj.get(field, [])
                inner_fields = set()
                for inner_obj in inner_objs:
                    inner_fields.update(inner_obj.keys())
                kmap = {}
                for k in inner_fields:
                    kmap[k] = f'{field}{sep}{k}'
                    obj[kmap[k]] = []
                for inner_obj in inner_objs:
                    for k, kmapped in kmap.items():
                        obj[kmapped].append(inner_obj.get(k,None))
                        fmap[k] = kmapped
        if config.delete:
            for obj in objs2:
                if field in obj:
                    del obj[field]
    return objs2

def unflatten(objs: List[dict], config: GlobalConfig = GlobalConfig()) -> List:
    """
    Reverses the flatten operation

    :param objs: list of dicts to be unflattened
    :param configmap:
    :param sep:
    :return:
    """
    sep = config.sep
    configmap = config.key_configs
    objs2 = [obj.copy() for obj in objs]
    for field, config in configmap.items():
        fmap = config.mappings
        serializers = config.serializers
        for serializer in serializers:
            f2 = _serialized_field_name(field, sep, serializer)
            for obj in objs2:
                if f2 in obj:
                    serialized_v = obj[f2]
                    if serialized_v is not None:
                        if serializer == Serializer.yaml:
                            nu_obj = yaml.safe_load(serialized_v)
                        elif serializer == Serializer.json:
                            print(f'Loading: {f2} in {obj}')
                            nu_obj = json.loads(serialized_v)
                        elif serializer == Serializer.pickle:
                            nu_obj = pickle.loads(serialized_v)
                        else:
                            raise Exception(f'unknown serializer: {serializer}')
                        obj[field] = nu_obj
                    del obj[f2]
                else:
                    logging.error(f'Expected: {f2} in {obj}')
        if config.flatten and not config.is_list:
            for obj in objs2:
                inner_obj = {}
                for ik, iv in fmap.items():
                    if iv in obj:
                        inner_obj[ik] = obj[iv]
                        del obj[iv]
                if field not in obj:
                    obj[field] = inner_obj
        if config.flatten and config.is_list:
            for obj in objs2:
                print(f'FMAP = {fmap}')
                fmap_actual = {ik: iv for ik, iv in fmap.items() if iv in obj and obj[iv] is not None and len(obj[iv]) > 0}
                print(f'FMAP_A = {fmap_actual}')
                if len(fmap_actual.values()) == 0:
                    logging.warning(f'Empty list for {field} for {obj}')
                    continue
                iv = list(fmap_actual.values())[0] # pick arbitrary
                inner_objs = [{} for x in obj[iv]]
                for i in range(0, len(inner_objs)):
                    inner_obj = inner_objs[i]
                    for ik, iv in fmap_actual.items():
                        inner_obj[ik] = obj[iv][i]
                if field not in obj:
                    obj[field] = inner_objs
                for iv in fmap.values():
                    if iv in obj:
                        del obj[iv]
    return objs2

def flatten_to_csv(objs, outstream, config: GlobalConfig = GlobalConfig(), **params):
    """
    Serialize a list of objects as a CSV

    :param objs:
    :param outstream: file-like object
    :param delimiter:
    :param internal_delimiter:
    :param params:
    :return:
    """
    delimiter = config.csv_delimiter
    internal_delimiter = config.csv_inner_delimiter
    list_parens = config.csv_list_quotes
    internal_delimiter_esc = f'\\{internal_delimiter}'
    lo, lc = list_parens
    def _serialize_as_str(x: Optional[Any]) -> str:
        if x is None:
            return ''
        else:
            return str(x).replace(internal_delimiter, internal_delimiter_esc)

    flat_objs = flatten(objs, config, **params)
    fieldnames = []
    for obj in flat_objs:
        for k in obj.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    w = csv.DictWriter(outstream, delimiter=delimiter, fieldnames=fieldnames, quoting=csv.QUOTE_NONE, escapechar="\\")
    w.writeheader()
    for obj in flat_objs:
        nu_obj = {}
        for k, v in obj.items():
            if isinstance(v, list):
                v = internal_delimiter.join([_serialize_as_str(x) for x in v])
                v = f'{lo}{v}{lc}'
            else:
                v = _serialize_as_str(v)
            nu_obj[k] = v.replace('\n', '\\n').replace('\t', '\\t')
        w.writerow(nu_obj)



def unflatten_from_csv(source, config: GlobalConfig = GlobalConfig(), **params):
    """
    Read serialized objects from a CSV file

    :param instream: file-like object
    :param delimiter:
    :param internal_delimiter:
    :param params:
    :return:
    """
    delimiter = config.csv_delimiter
    internal_delimiter = config.csv_inner_delimiter
    list_parens = config.csv_list_quotes
    if isinstance(source, str):
        instream = open(source)
    else:
        instream = source
    r = csv.DictReader(instream, delimiter=delimiter, quoting=csv.QUOTE_NONE, escapechar="\\")

    lo, lc = list_parens
    def _getval(x: str) -> Optional[Any]:
        if x == '':
            return None
        else:
            try:
                return int(x)
            except ValueError:
                try:
                    return float(x)
                except ValueError:
                    return x

    objs = []
    for row in r:
        nu_obj = {}
        for k, v in row.items():
            v = v.replace('\\n', '\n').replace('\\t', '\t')
            # TODO: document rules
            if (lo != '' or lc != '') and v.startswith(lo) and v.endswith(lc) and not k.endswith('_json'):
                v = v[1:-1]
                # TODO: escaping
                v = [_getval(x) for x in v.split(internal_delimiter)]
            else:
                v = _getval(v)
            nu_obj[k] = v
        objs.append(nu_obj)
    return unflatten(objs, config, **params)
