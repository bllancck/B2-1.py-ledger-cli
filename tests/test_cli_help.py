"""Tests for complete and consistent CLI help output."""

import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from budget_app.cli import build_parser, main


REQUIRED_COMMANDS = {
    "add",
    "list",
    "search",
    "summary",
    "budget",
    "category",
    "update",
    "delete",
    "import",
    "export",
}


class CliHelpTest(unittest.TestCase):
    def capture_help(self, arguments: list[str]) -> str:
        """Run one help request and return its standard output."""
        with redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as raised:
                main([*arguments, "--help"])
        self.assertEqual(raised.exception.code, 0)
        return output.getvalue()

    def test_top_level_help_lists_all_required_commands(self) -> None:
        help_output = self.capture_help([])

        for command in REQUIRED_COMMANDS:
            with self.subTest(command=command):
                self.assertIn(command, help_output)

    def test_every_command_and_action_provides_help(self) -> None:
        help_paths = (
            ["add"],
            ["list"],
            ["search"],
            ["summary"],
            ["budget"],
            ["budget", "set"],
            ["category"],
            ["category", "add"],
            ["category", "list"],
            ["category", "remove"],
            ["update"],
            ["delete"],
            ["import"],
            ["export"],
        )

        for path in help_paths:
            with self.subTest(path=path):
                self.assertIn("usage:", self.capture_help(path))

    def test_help_lists_each_command_required_options(self) -> None:
        expected_options = {
            ("list",): ("--limit",),
            ("search",): (
                "--from",
                "--to",
                "--category",
                "--type",
                "--q",
                "--tag",
            ),
            ("summary",): ("--month", "--top"),
            ("budget", "set"): ("--month", "--amount"),
            ("update",): (
                "--id",
                "--date",
                "--type",
                "--category",
                "--amount",
                "--memo",
                "--tags",
            ),
            ("delete",): ("--id",),
            ("import",): ("--from",),
            ("export",): ("--out", "--month", "--from", "--to"),
        }

        for path, options in expected_options.items():
            with self.subTest(path=path):
                help_output = self.capture_help(list(path))
                for option in options:
                    self.assertIn(option, help_output)

    def test_custom_options_use_double_dash(self) -> None:
        parsers = [build_parser()]

        while parsers:
            parser = parsers.pop()
            for action in parser._actions:
                for option in action.option_strings:
                    if option != "-h":
                        self.assertTrue(option.startswith("--"), option)
                if isinstance(action, argparse._SubParsersAction):
                    parsers.extend(action.choices.values())

    def test_help_does_not_create_custom_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "help-only-data"

            with redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["--data-dir", str(data_dir), "list", "--help"])

            self.assertEqual(raised.exception.code, 0)
            self.assertFalse(data_dir.exists())


if __name__ == "__main__":
    unittest.main()
