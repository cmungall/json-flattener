import json
import tempfile
import unittest
from typing import Optional

from click.testing import CliRunner

from json_flattener.cli import main
from tests import INPUT

FLATTEN = "flatten"
UNFLATTEN = "unflatten"


class TestCommandLineInterface(unittest.TestCase):
    """
    Tests all command-line subcommands
    """

    def setUp(self) -> None:
        runner = CliRunner(mix_stderr=False)
        self.runner = runner

    def test_main_help(self):
        """Tests parent command."""
        result = self.runner.invoke(main, ["--help"])
        out = result.stdout
        self.assertEqual("", result.stderr)
        self.assertIn("flatten", out)
        self.assertIn("unflatten", out)
        self.assertEqual(0, result.exit_code)

    def test_roundtrip(self):
        """Tests flatten subcommand."""
        opts = ["-C", "creator=flat", "-C", "books=multivalued"]
        result = self.runner.invoke(main, [FLATTEN, "-i", INPUT] + opts)
        out = result.stdout
        # self.assertIn("S001\tLord of the Rings\t[fantasy]", out)
        self.assertEqual(0, result.exit_code)
        out_file = tempfile.NamedTemporaryFile("w")
        conf_file = tempfile.NamedTemporaryFile("w")
        result = self.runner.invoke(
            main,
            [FLATTEN, "-i", INPUT, "-o", out_file.name, "-O", conf_file.name]
            + opts,
        )
        with open(out_file.name) as file:
            out = "".join(file.readlines())
            # print(out)
            self.assertIn("S001\tLord of the Rings\t[fantasy]", out)
        out_file2 = tempfile.NamedTemporaryFile("w")
        result = self.runner.invoke(
            main,
            [
                UNFLATTEN,
                "-i",
                out_file.name,
                "-o",
                out_file2.name,
                "-c",
                conf_file.name,
            ]
            + opts,
        )
        self.assertEqual(0, result.exit_code)
        with open(out_file2.name) as file:
            objs = json.load(file)
            [obj1] = [obj for obj in objs if obj["id"] == "S001"]
            #print(obj1)
            self.assertEqual(
                {
                    "books": [
                        {
                            "id": "S001.1",
                            "name": "Fellowship of the Ring",
                            "price": 5.99,
                            "summary": "Hobbits",
                        },
                        {
                            "id": "S001.2",
                            "name": "The Two Towers",
                            "price": 5.99,
                            "summary": "More hobbits",
                        },
                        {
                            "id": "S001.3",
                            "name": "Return of the King",
                            "price": 6.99,
                            "summary": "Yet more hobbits",
                        },
                    ],
                    "creator": {
                        "from_country": "England",
                        "name": "JRR Tolkein",
                    },
                    "genres": ["fantasy"],
                    "id": "S001",
                    "name": "Lord of the Rings",
                },
                obj1,
            )
