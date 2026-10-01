"""Tests for shared CLI error handling."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout

from budget_app.cli import main
from budget_app.decorators import handle_cli_errors


class CliErrorDecoratorTest(unittest.TestCase):
    def test_returns_wrapped_result_when_no_error_occurs(self) -> None:
        @handle_cli_errors
        def successful_command() -> int:
            return 0

        self.assertEqual(successful_command(), 0)

    def test_value_error_prints_cause_and_hint_without_traceback(self) -> None:
        @handle_cli_errors
        def invalid_command() -> int:
            raise ValueError("잘못된 테스트 값")

        with redirect_stdout(io.StringIO()) as output:
            exit_code = invalid_command()

        result = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("[오류] 잘못된 테스트 값", result)
        self.assertIn("[힌트]", result)
        self.assertNotIn("Traceback", result)

    def test_os_error_prints_file_hint(self) -> None:
        @handle_cli_errors
        def unreadable_command() -> int:
            raise OSError("permission denied")

        with redirect_stdout(io.StringIO()) as output:
            exit_code = unreadable_command()

        result = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("파일을 처리할 수 없습니다", result)
        self.assertIn("파일 권한", result)

    def test_actual_command_uses_shared_error_format(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "list",
                        "--limit",
                        "0",
                    ]
                )

        result = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("[오류] 조회 건수", result)
        self.assertIn("[힌트]", result)
        self.assertNotIn("Traceback", result)


if __name__ == "__main__":
    unittest.main()
