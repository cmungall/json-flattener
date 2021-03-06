import os
import unittest
import json
import yaml
import io
import logging
from json_flattener import flatten, unflatten, KeyConfig, GlobalConfig, Serializer, flatten_to_csv, unflatten_from_csv

ROOT = os.path.abspath(os.path.dirname(__file__))
INPUT_DIR = os.path.join(ROOT, 'inputs')
INPUT = os.path.join(INPUT_DIR, 'books1.yaml')

def _json(obj) -> str:
    return json.dumps(obj, indent=' ', sort_keys=True)


def _roundtrip_to_tsv(objs, config=None, **params):
    """
    Convert json objects to TSV and convert back
    """
    output = io.StringIO()
    flatten_to_csv(objs, output, config=config, **params)
    #print(f'CONFIG:')
    config_dict = config.as_dict()
    #print(_json(config_dict))
    config2 = GlobalConfig.from_dict(**config_dict)
    print(f'C2 = {config2}')
    print('AS TSV')
    print(output.getvalue())
    inp = io.StringIO(output.getvalue())
    objs2 = unflatten_from_csv(inp, config=config, **params)
    logging.info('BACK FROM TSV')
    logging.info(_json(objs2))
    logging.info('ORIG')
    logging.info(_json(objs))
    assert objs == objs2

class FlattenerCase(unittest.TestCase):

    def test_flattener(self):

        dict = {
            "id": "A1",
            "subject": {
                "id": "G1",
                "name": "gene1",
                "category": "gene"
            },
            "object": {
                "id": "T1",
                "name": "term1",
                "category": "term"
            },
            "publications": ["PMID1", "PMID2"],
            "closure": [
                {"id": "X1", "name": "x1"},
                {"id": "X2", "name": "x2"},
                {"id": "X3", "name": "x3"},
            ]
        }
        objs = [dict]
        original_objs_json = _json(objs)
        print('ORIG')
        print(original_objs_json)

        # test1: mixture of YAML serialization for some keys, and flattening for others
        kconfig = {"subject": KeyConfig(delete=True, serializers='yaml'),
                  "object": KeyConfig(delete=True, flatten=True),
                  "closure": KeyConfig(delete=True, is_list=True, flatten=True)}
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        print('ORIGINAL 1:')
        print(_json(objs))
        print('FLATTENED 1:')
        print(_json(flattened_objs))
        for obj in flattened_objs:
            assert 'subject_yaml' in obj
            assert 'object_id' in obj
            assert 'object_name' in obj
            assert 'object_category' in obj
            assert 'closure_id' in obj
            assert 'closure_name' in obj
            assert 'subject' not in obj
            assert 'object' not in obj
            assert 'closure' not in obj
        _roundtrip_to_tsv(objs, config=config)
        roundtripped_objs = unflatten(flattened_objs, config)
        print('ORIGINAL 1b:')
        print(_json(objs))
        print('ROUNDTRIP 1:')
        roundtrip_json = _json(roundtripped_objs)
        print(roundtrip_json)
        assert roundtripped_objs == objs
        assert roundtrip_json == original_objs_json

        # test2: as above, but use json, and . as separator
        kconfig = {"subject": KeyConfig(delete=True, serializers=['json']),
                  "object": KeyConfig(delete=True, flatten=True),
                  "closure": KeyConfig(delete=True, is_list=True, flatten=True)}
        config = GlobalConfig(key_configs=kconfig, sep='.')
        flattened_objs = flatten(objs, config)
        print('FLATTENED 2:')
        print(_json(flattened_objs))
        for obj in flattened_objs:
            assert 'subject.json' in obj
            assert 'object.id' in obj
            assert 'object.name' in obj
            assert 'object.category' in obj
            assert 'closure.id' in obj
            assert 'closure.name' in obj
            assert 'subject' not in obj
            assert 'object' not in obj
            assert 'closure' not in obj
        roundtripped_objs = unflatten(flattened_objs, config)
        print('ROUNDTRIP 2:')
        print(_json(roundtripped_objs))
        assert roundtripped_objs == objs

        # test3: as above, but use pickle, and / as separator
        kconfig = {"subject": KeyConfig(delete=True, serializers='pickle'),
                  "object": KeyConfig(delete=True, flatten=True),
                  "closure": KeyConfig(delete=True, is_list=True, flatten=True)}
        config = GlobalConfig(key_configs=kconfig, sep='/')
        flattened_objs = flatten(objs, config)
        print('FLATTENED 3:')
        print(flattened_objs)
        for obj in flattened_objs:
            assert 'subject/pickle' in obj
            assert 'object/id' in obj
            assert 'object/name' in obj
            assert 'object/category' in obj
            assert 'closure/id' in obj
            assert 'closure/name' in obj
            assert 'subject' not in obj
            assert 'object' not in obj
            assert 'closure' not in obj
        roundtripped_objs = unflatten(flattened_objs, config)
        print('ROUNDTRIP 3:')
        print(_json(roundtripped_objs))
        assert roundtripped_objs == objs

        # test 4: as test 1, but no do delete keys in transform
        kconfig = {"subject": KeyConfig(delete=False, serializers='yaml'),
                  "object": KeyConfig(delete=False, flatten=True),
                  "closure": KeyConfig(delete=False, is_list=True, flatten=True)}
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        print('ORIGINAL 4:')
        print(_json(objs))
        print('FLATTENED 4:')
        print(_json(flattened_objs))
        for obj in flattened_objs:
            assert 'subject_yaml' in obj
            assert 'object_id' in obj
            assert 'object_name' in obj
            assert 'object_category' in obj
            assert 'closure_id' in obj
            assert 'closure_name' in obj
            # we do NOT delete the originals
            assert 'subject' in obj
            assert 'object' in obj
            assert 'closure' in obj
        roundtripped_objs = unflatten(flattened_objs, config)
        print('ROUNDTRIP 4:')
        roundtrip_json = _json(roundtripped_objs)
        print(roundtrip_json)
        assert roundtripped_objs == objs
        assert roundtrip_json == original_objs_json

        # test 5: stringify (no reverse)
        kconfig = {"subject": KeyConfig(delete=True, serializers=[Serializer.as_str]),
                  "object": KeyConfig(delete=True, serializers=[Serializer.as_str]),
                  "closure": KeyConfig(delete=True, serializers=[Serializer.as_str])}
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        print('ORIGINAL 5:')
        print(_json(objs))
        print('FLATTENED 5:')
        print(_json(flattened_objs))
        for obj in flattened_objs:
            assert 'subject_as_str' in obj
            assert 'object_as_str' in obj
            assert 'closure_as_str' in obj
            assert 'subject' not in obj
            assert 'object' not in obj
            assert 'closure' not in obj

        # test6: as test 1 but with no []s around lists, and explicit list assignment
        kconfig = {"subject": KeyConfig(delete=True, serializers='yaml'),
                   "object": KeyConfig(delete=True, flatten=True),
                   "closure": KeyConfig(delete=True, is_list=True, flatten=True),
                   "publications": KeyConfig(is_list=True),
                   # TODO: these should be inferred
                   "closure_id": KeyConfig(is_list=True),
                   "closure_name": KeyConfig(is_list=True),
                   }
        config = GlobalConfig(key_configs=kconfig, csv_list_markers=('', ''))
        flattened_objs = flatten(objs, config)
        print('ORIGINAL 1:')
        print(_json(objs))
        print('FLATTENED 1:')
        print(_json(flattened_objs))
        for obj in flattened_objs:
            assert 'subject_yaml' in obj
            assert 'object_id' in obj
            assert 'object_name' in obj
            assert 'object_category' in obj
            assert 'closure_id' in obj
            assert 'closure_name' in obj
            assert 'subject' not in obj
            assert 'object' not in obj
            assert 'closure' not in obj
        _roundtrip_to_tsv(objs, config=config)
        roundtripped_objs = unflatten(flattened_objs, config)
        print('ORIGINAL 1b:')
        print(_json(objs))
        print('ROUNDTRIP 1:')
        roundtrip_json = _json(roundtripped_objs)
        print(roundtrip_json)
        assert roundtripped_objs == objs
        assert roundtrip_json == original_objs_json

        # test 7: melt (no reverse)
        kconfig = {"subject": KeyConfig(delete=True, serializers=[Serializer.as_str]),
                   "object": KeyConfig(delete=True, serializers=[Serializer.as_str]),
                   "closure": KeyConfig(delete=True, is_list=True, flatten=True, melt_list_elements=True),
                   "publications": KeyConfig(delete=True, melt_list_elements=True)}
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        print('ORIGINAL 7:')
        print(_json(objs))
        print('FLATTENED 7:')
        print(_json(flattened_objs))
        for obj in flattened_objs:
            assert 'subject_as_str' in obj
            assert 'object_as_str' in obj
            assert 'PMID1' in obj
            assert 'x1' in obj
            assert 'X1' in obj
            assert 'publications' not in obj
            assert 'subject' not in obj
            assert 'object' not in obj

    def test_lists(self):
        obj = {
            "id": "X1",
            "my_list": [
                {"x": "foo", "y": 2},
                {"x": "bar", "y": 3},
            ]
        }
        key_config = {"my_list": KeyConfig(delete=True, flatten=True, is_list=True, serializers=[Serializer.json])}
        global_config = GlobalConfig(key_configs=key_config)
        _roundtrip_to_tsv([obj], global_config)
        key_config = {"my_list": KeyConfig(delete=True, flatten=False, is_list=True, serializers=[Serializer.json])}
        global_config = GlobalConfig(key_configs=key_config)
        _roundtrip_to_tsv([obj], global_config)
        key_config = {"my_list": KeyConfig(delete=False, flatten=True, is_list=True, serializers=[Serializer.json])}
        global_config = GlobalConfig(key_configs=key_config)
        _roundtrip_to_tsv([obj], global_config)
        key_config = {"my_list": KeyConfig(delete=False, flatten=False, is_list=True, serializers=[Serializer.json])}
        global_config = GlobalConfig(key_configs=key_config)
        _roundtrip_to_tsv([obj], global_config)

    def test_nulls(self):

        dict = {
            "id": "series001",
            "name": "LOTR",
            "books": [
                {"id": "B1",
                "name": "FOTR",
                "price": 2.99},
                {"id": "B2",
                 "name": "TTT",
                 "price": 3.99},
                {"id": "B3",
                 "name": "ROTK",
                 "price": 4.99}]}
        for i in range(0, 3):
            s = dict.copy()
            # make empty
            #del s['books'][i]['price']
            #s['books'][i]['price'] = None
            del s['books'][i]['price']
            objs = [s]
            original_objs_json = _json(objs)
            print(original_objs_json)
            kconfig = {"books": KeyConfig(delete=True, flatten=True, is_list=True)}
            config = GlobalConfig(key_configs=kconfig)
            flattened_objs = flatten(objs, config)
            print(f'ORIGINAL n {i}:')
            print(_json(objs))
            print(f'FLATTENED n {i}:')
            print(_json(flattened_objs))
            for obj in flattened_objs:
                assert 'id' in obj
                assert 'name' in obj
                assert 'books' not in obj
                assert 'books_id' in obj
                assert 'books_name' in obj
                #assert 'books_price' in obj
            roundtripped_objs = unflatten(flattened_objs, config)
            print(f'ROUNDTRIP {i}:')
            roundtrip_json = _json(roundtripped_objs)
            print(roundtrip_json)
            assert roundtripped_objs == objs
            assert roundtrip_json == original_objs_json
            _roundtrip_to_tsv(objs, config=config)

    def test_books(self):
        with open(INPUT) as stream:
            shop = yaml.safe_load(stream)
        objs = shop['all_book_series']
        kconfig = {"creator": KeyConfig(delete=True, flatten=True),
                   "books": KeyConfig(delete=True, is_list=True, flatten=True)}
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        #print(_json(config))
        print('BOOKS, flattened:')
        print(_json(flattened_objs))
        #config.key_configs['books'].mappings = None
        roundtripped_objs = unflatten(flattened_objs, config)
        roundtrip_json = _json(roundtripped_objs)
        print('BOOKS, roundtripped:')
        print(roundtrip_json)
        _roundtrip_to_tsv(objs, config=config)

if __name__ == '__main__':
    unittest.main()
