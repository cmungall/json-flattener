import json
import logging
import tempfile
import unittest
from pathlib import Path
from typing import Optional

from click.testing import CliRunner

from json_flattener.cli import main
from tests import INPUT, OUTPUT_DIR

FLATTEN = "flatten"
UNFLATTEN = "unflatten"


class TestCommandLineInterface(unittest.TestCase):
    """
    Tests all command-line subcommands
    """

    def setUp(self) -> None:
        runner = CliRunner(mix_stderr=False)
        self.runner = runner
        outdir = Path(OUTPUT_DIR)
        outdir.mkdir(parents=True, exist_ok=True)

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
        self.assertEqual(0, result.exit_code)
        out_file = str(Path(OUTPUT_DIR) / "out.csv")
        conf_file = str(Path(OUTPUT_DIR) / "conf.json")
        result = self.runner.invoke(
            main,
            [FLATTEN, "-i", INPUT, "-o", out_file, "-O", conf_file]
            + opts,
        )
        with open(out_file) as file:
            out = "".join(file.readlines())
            # print(out)
            self.assertIn("S001\tLord of the Rings\t[fantasy]", out)
        out_file2 = str(Path(OUTPUT_DIR) / "out2.csv")
        result = self.runner.invoke(
            main,
            [
                UNFLATTEN,
                "-i",
                out_file,
                "-o",
                out_file2,
                "-c",
                conf_file,
            ]
            + opts,
        )
        self.assertEqual(0, result.exit_code)
        with open(out_file2) as file:
            objs = json.load(file)
            [obj1] = [obj for obj in objs if obj["id"] == "S001"]
            # print(obj1)
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
