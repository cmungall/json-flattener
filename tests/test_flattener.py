"""Tests all public functions."""

import io
import json
import logging
import unittest
from pathlib import Path
from typing import Any, List

import yaml

from json_flattener import (
    GlobalConfig,
    KeyConfig,
    Serializer,
    flatten,
    flatten_to_csv,
    unflatten,
    unflatten_from_csv,
)
from json_flattener.flattener import MissingColumnError
from tests import INPUT, INPUT_DIR


def _json(obj) -> str:
    return json.dumps(obj, indent=" ", sort_keys=True)


class FlattenerCase(unittest.TestCase):
    """Test full functionality."""

    def _roundtrip_to_tsv(
        self, objs: List[Any], config: GlobalConfig = None, **params
    ):
        """
        Convert json objects to TSV and convert back.

        Performs a round trip through flatten followed by unflatten.
        """
        output = io.StringIO()
        flatten_to_csv(objs, output, config=config, **params)
        # logging.info(f'CONFIG:')
        config_dict = config.as_dict()
        # logging.info(_json(config_dict))
        config2 = GlobalConfig.from_dict(**config_dict)
        logging.info(f"C2 = {config2}")
        logging.info("AS TSV")
        logging.info(output.getvalue())
        inp = io.StringIO(output.getvalue())
        objs2 = unflatten_from_csv(inp, config=config, **params)
        logging.info("BACK FROM TSV")
        logging.info(_json(objs2))
        logging.info("ORIG")
        logging.info(_json(objs))
        self.assertEqual(objs, objs2)

    def test_flattener(self):
        """
        Tests core functionality.

        Uses artificial dict example.
        """
        dict = {
            "id": "A1",
            "subject": {"id": "G1", "name": "gene1", "category": "gene"},
            "object": {"id": "T1", "name": "term1", "category": "term"},
            "publications": ["PMID1", "PMID2"],
            "closure": [
                {"id": "X1", "name": "x1"},
                {"id": "X2", "name": "x2"},
                {"id": "X3", "name": "x3"},
            ],
        }
        objs = [dict]
        original_objs_json = _json(objs)
        logging.info("ORIG")
        logging.info(original_objs_json)

        # test1: mixture of YAML serialization
        # for some keys, and flattening for others
        kconfig = {
            "subject": KeyConfig(delete=True, serializers="yaml"),
            "object": KeyConfig(delete=True, flatten=True),
            "closure": KeyConfig(delete=True, is_list=True, flatten=True),
        }
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        logging.info("ORIGINAL 1:")
        logging.info(_json(objs))
        logging.info("FLATTENED 1:")
        logging.info(_json(flattened_objs))
        for obj in flattened_objs:
            self.assertIn("subject_yaml", obj)
            self.assertIn("object_id", obj)
            self.assertIn("object_name", obj)
            self.assertIn("object_category", obj)
            self.assertIn("closure_id", obj)
            self.assertIn("closure_name", obj)
            assert "subject" not in obj
            assert "object" not in obj
            assert "closure" not in obj
        self._roundtrip_to_tsv(objs, config=config)
        roundtripped_objs = unflatten(flattened_objs, config)
        logging.info("ORIGINAL 1b:")
        logging.info(_json(objs))
        logging.info("ROUNDTRIP 1:")
        roundtrip_json = _json(roundtripped_objs)
        logging.info(roundtrip_json)
        self.assertEqual(roundtripped_objs, objs)
        self.assertEqual(roundtrip_json, original_objs_json)
        # test2: as above, but use json, and . as separator
        kconfig = {
            "subject": KeyConfig(delete=True, serializers=["json"]),
            "object": KeyConfig(delete=True, flatten=True),
            "closure": KeyConfig(delete=True, is_list=True, flatten=True),
        }
        config = GlobalConfig(key_configs=kconfig, sep=".")
        flattened_objs = flatten(objs, config)
        logging.info("FLATTENED 2:")
        logging.info(_json(flattened_objs))
        for obj in flattened_objs:
            self.assertIn("subject.json", obj)
            self.assertIn("object.id", obj)
            self.assertIn("object.name", obj)
            self.assertIn("object.category", obj)
            self.assertIn("closure.id", obj)
            self.assertIn("closure.name", obj)
            assert "subject" not in obj
            assert "object" not in obj
            assert "closure" not in obj
        roundtripped_objs = unflatten(flattened_objs, config)
        logging.info("ROUNDTRIP 2:")
        logging.info(_json(roundtripped_objs))
        self.assertEqual(roundtripped_objs, objs)
        # test3: as above, but use pickle, and / as separator
        kconfig = {
            "subject": KeyConfig(delete=True, serializers="pickle"),
            "object": KeyConfig(delete=True, flatten=True),
            "closure": KeyConfig(delete=True, is_list=True, flatten=True),
        }
        config = GlobalConfig(key_configs=kconfig, sep="/")
        flattened_objs = flatten(objs, config)
        logging.info("FLATTENED 3:")
        logging.info(flattened_objs)
        for obj in flattened_objs:
            self.assertIn("subject/pickle", obj)
            self.assertIn("object/id", obj)
            self.assertIn("object/name", obj)
            self.assertIn("object/category", obj)
            self.assertIn("closure/id", obj)
            self.assertIn("closure/name", obj)
            assert "subject" not in obj
            assert "object" not in obj
            assert "closure" not in obj
        roundtripped_objs = unflatten(flattened_objs, config)
        logging.info("ROUNDTRIP 3:")
        logging.info(_json(roundtripped_objs))
        self.assertEqual(roundtripped_objs, objs)
        # test 4: as test 1, but no do delete keys in transform
        kconfig = {
            "subject": KeyConfig(delete=False, serializers="yaml"),
            "object": KeyConfig(delete=False, flatten=True),
            "closure": KeyConfig(delete=False, is_list=True, flatten=True),
        }
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        logging.info("ORIGINAL 4:")
        logging.info(_json(objs))
        logging.info("FLATTENED 4:")
        logging.info(_json(flattened_objs))
        for obj in flattened_objs:
            self.assertIn("subject_yaml", obj)
            self.assertIn("object_id", obj)
            self.assertIn("object_name", obj)
            self.assertIn("object_category", obj)
            self.assertIn("closure_id", obj)
            self.assertIn("closure_name", obj)
            # we do NOT delete the originals
            self.assertIn("subject", obj)
            self.assertIn("object", obj)
            self.assertIn("closure", obj)
        roundtripped_objs = unflatten(flattened_objs, config)
        logging.info("ROUNDTRIP 4:")
        roundtrip_json = _json(roundtripped_objs)
        logging.info(roundtrip_json)
        self.assertEqual(roundtripped_objs, objs)
        self.assertEqual(roundtrip_json, original_objs_json)
        # test 5: stringify (no reverse)
        kconfig = {
            "subject": KeyConfig(delete=True, serializers=[Serializer.as_str]),
            "object": KeyConfig(delete=True, serializers=[Serializer.as_str]),
            "closure": KeyConfig(delete=True, serializers=[Serializer.as_str]),
        }
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        logging.info("ORIGINAL 5:")
        logging.info(_json(objs))
        logging.info("FLATTENED 5:")
        logging.info(_json(flattened_objs))
        for obj in flattened_objs:
            self.assertIn("subject_as_str", obj)
            self.assertIn("object_as_str", obj)
            self.assertIn("closure_as_str", obj)
            assert "subject" not in obj
            assert "object" not in obj
            assert "closure" not in obj
        # test6: as test 1 but with no []s around lists,
        # and explicit list assignment
        kconfig = {
            "subject": KeyConfig(delete=True, serializers=["yaml"]),
            "object": KeyConfig(delete=True, flatten=True),
            "closure": KeyConfig(delete=True, is_list=True, flatten=True),
            "publications": KeyConfig(is_list=True),
            # TODO: these should be inferred
            "closure_id": KeyConfig(is_list=True),
            "closure_name": KeyConfig(is_list=True),
        }
        config = GlobalConfig(key_configs=kconfig, csv_list_markers=("", ""))
        flattened_objs = flatten(objs, config)
        logging.info("ORIGINAL 1:")
        logging.info(_json(objs))
        logging.info("FLATTENED 1:")
        logging.info(_json(flattened_objs))
        for obj in flattened_objs:
            self.assertIn("subject_yaml", obj)
            self.assertIn("object_id", obj)
            self.assertIn("object_name", obj)
            self.assertIn("object_category", obj)
            self.assertIn("closure_id", obj)
            self.assertIn("closure_name", obj)
            assert "subject" not in obj
            assert "object" not in obj
            assert "closure" not in obj
        self._roundtrip_to_tsv(objs, config=config)
        roundtripped_objs = unflatten(flattened_objs, config)
        logging.info("ORIGINAL 1b:")
        logging.info(_json(objs))
        logging.info("ROUNDTRIP 1:")
        roundtrip_json = _json(roundtripped_objs)
        logging.info(roundtrip_json)
        self.assertEqual(roundtripped_objs, objs)
        self.assertEqual(roundtrip_json, original_objs_json)
        # test 7: melt (no reverse)
        kconfig = {
            "subject": KeyConfig(delete=True, serializers=[Serializer.as_str]),
            "object": KeyConfig(delete=True, serializers=[Serializer.as_str]),
            "closure": KeyConfig(
                delete=True, is_list=True, flatten=True, melt_list_elements=True
            ),
            "publications": KeyConfig(delete=True, melt_list_elements=True),
        }
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        logging.info("ORIGINAL 7:")
        logging.info(_json(objs))
        logging.info("FLATTENED 7:")
        logging.info(_json(flattened_objs))
        for obj in flattened_objs:
            self.assertIn("subject_as_str", obj)
            self.assertIn("object_as_str", obj)
            self.assertIn("PMID1", obj)
            self.assertIn("x1", obj)
            self.assertIn("X1", obj)
            assert "publications" not in obj
            assert "subject" not in obj
            assert "object" not in obj

    def test_lists(self):
        """Tests list behavior."""
        obj = {
            "id": "X1",
            "my_list": [
                {"x": "foo", "y": 2},
                {"x": "bar", "y": 3},
            ],
        }
        key_config = {
            "my_list": KeyConfig(
                delete=True,
                flatten=True,
                is_list=True,
                serializers=[Serializer.json],
            )
        }
        global_config = GlobalConfig(key_configs=key_config)
        self._roundtrip_to_tsv([obj], global_config)
        key_config = {
            "my_list": KeyConfig(
                delete=True,
                flatten=False,
                is_list=True,
                serializers=[Serializer.json],
            )
        }
        global_config = GlobalConfig(key_configs=key_config)
        self._roundtrip_to_tsv([obj], global_config)
        key_config = {
            "my_list": KeyConfig(
                delete=False,
                flatten=True,
                is_list=True,
                serializers=[Serializer.json],
            )
        }
        global_config = GlobalConfig(key_configs=key_config)
        self._roundtrip_to_tsv([obj], global_config)
        key_config = {
            "my_list": KeyConfig(
                delete=False,
                flatten=False,
                is_list=True,
                serializers=[Serializer.json],
            )
        }
        global_config = GlobalConfig(key_configs=key_config)
        self._roundtrip_to_tsv([obj], global_config)

    def test_nulls(self):
        """
        Tests behavior with python "None".

        Also checks 'delete' in KeyConfig.
        """

        dict = {
            "id": "series001",
            "name": "LOTR",
            "books": [
                {"id": "B1", "name": "FOTR", "price": 2.99},
                {"id": "B2", "name": "TTT", "price": 3.99},
                {"id": "B3", "name": "ROTK", "price": 4.99},
            ],
        }
        for i in range(0, 3):
            s = dict.copy()
            # make empty
            # del s['books'][i]['price']
            # s['books'][i]['price'] = None
            del s["books"][i]["price"]
            objs = [s]
            original_objs_json = _json(objs)
            logging.info(original_objs_json)
            kconfig = {
                "books": KeyConfig(delete=True, flatten=True, is_list=True)
            }
            config = GlobalConfig(key_configs=kconfig)
            flattened_objs = flatten(objs, config)
            logging.info(f"ORIGINAL n {i}:")
            logging.info(_json(objs))
            logging.info(f"FLATTENED n {i}:")
            logging.info(_json(flattened_objs))
            for obj in flattened_objs:
                self.assertIn("id", obj)
                self.assertIn("name", obj)
                assert "books" not in obj
                self.assertIn("books_id", obj)
                self.assertIn("books_name", obj)
                # self.assertIn('books_price', obj)
            roundtripped_objs = unflatten(flattened_objs, config)
            logging.info(f"ROUNDTRIP {i}:")
            roundtrip_json = _json(roundtripped_objs)
            logging.info(roundtrip_json)
            self.assertEqual(roundtripped_objs, objs)

            self.assertEqual(roundtrip_json, original_objs_json)

            self._roundtrip_to_tsv(objs, config=config)

    def test_roundtrip_from_file(self):
        """
        Tests core functionality.

        Uses books example
        """
        with open(INPUT) as stream:
            shop = yaml.safe_load(stream)
        objs = shop["all_book_series"]
        kconfig = {
            "creator": KeyConfig(delete=True, flatten=True),
            "books": KeyConfig(delete=True, is_list=True, flatten=True),
        }
        config = GlobalConfig(key_configs=kconfig)
        flattened_objs = flatten(objs, config)
        # logging.info(_json(config))
        logging.info("BOOKS, flattened:")
        logging.info(_json(flattened_objs))
        # config.key_configs['books'].mappings = None
        print(config)
        roundtripped_objs = unflatten(flattened_objs, config)
        # for o in roundtripped_objs:
        #    print(o)
        roundtrip_json = _json(roundtripped_objs)
        logging.info("BOOKS, roundtripped:")
        logging.info(roundtrip_json)
        self._roundtrip_to_tsv(objs, config=config)

    def test_badly_formatted(self):
        """
        Tests graceful failure on badly formatted TSV input.
        """
        with open(str(Path(INPUT_DIR) / "badly-formatted.tsv")) as stream:
            with self.assertRaises(MissingColumnError) as _e:
                _objs = unflatten_from_csv(stream)


if __name__ == "__main__":
    unittest.main()
