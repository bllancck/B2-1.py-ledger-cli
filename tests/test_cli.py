"""Tests for CLI initialization and top-level error handling."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from budget_app.cli import main


class CliInitializationTest(unittest.TestCase):
    def test_initialization_error_is_reported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_path = Path(temporary_directory) / "not-a-directory"
            data_path.write_text("file", encoding="utf-8")

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(["--data-dir", str(data_path)])

        result = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("[오류] 파일을 처리할 수 없습니다", result)
        self.assertIn("[힌트]", result)
        self.assertNotIn("Traceback", result)


if __name__ == "__main__":
    unittest.main()
