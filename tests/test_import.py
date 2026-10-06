"""Tests for transaction CSV imports."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from budget_app.cli import main
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.services import ImportService, TransactionService


class ImportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)
        self.categories = CategoryRepository(self.data_dir)
        self.categories.append("food")
        self.categories.append("salary")
        self.transactions = TransactionRepository(self.data_dir)
        self.service = ImportService(
            TransactionService(self.transactions, self.categories)
        )

    def write_csv(self, contents: str, filename: str = "input.csv") -> Path:
        """Write one UTF-8 CSV fixture in the temporary directory."""
        csv_path = self.data_dir / filename
        csv_path.write_text(contents, encoding="utf-8")
        return csv_path

    def test_imports_valid_rows_with_optional_values_and_tags(self) -> None:
        csv_path = self.write_csv(
            "date,type,category,amount,memo,tags\n"
            '2026-10-01,expense,food,15000,점심,"meal,lunch"\n'
            "2026-10-02,income,salary,3000000,,\n"
        )

        result = self.service.import_csv(csv_path)
        transactions = list(self.transactions.iter_all())

        self.assertEqual(result.imported, 2)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(transactions[0].tags, ["meal", "lunch"])
        self.assertEqual(transactions[1].memo, "")
        self.assertNotEqual(transactions[0].id, transactions[1].id)

    def test_optional_headers_may_be_omitted(self) -> None:
        csv_path = self.write_csv(
            "date,type,category,amount\n"
            "2026-10-01,expense,food,15000\n"
        )

        result = self.service.import_csv(csv_path)
        transaction = next(self.transactions.iter_all())

        self.assertEqual(result.imported, 1)
        self.assertEqual(transaction.memo, "")
        self.assertEqual(transaction.tags, [])

    def test_skips_invalid_rows_and_continues_importing(self) -> None:
        csv_path = self.write_csv(
            "date,type,category,amount,memo,tags\n"
            "2026-10-01,expense,food,15000,valid,meal\n"
            "2026-02-30,expense,food,1000,bad date,\n"
            "2026-10-02,expense,unknown,1000,bad category,\n"
            "2026-10-03,expense,food,0,bad amount,\n"
        )

        result = self.service.import_csv(csv_path)

        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped, 3)
        self.assertEqual(
            [row.line_number for row in result.skipped_rows],
            [3, 4, 5],
        )
        self.assertEqual(len(list(self.transactions.iter_all())), 1)

    def test_rejects_csv_without_required_headers(self) -> None:
        csv_path = self.write_csv("date,type,amount\n2026-10-01,expense,1000\n")

        with self.assertRaisesRegex(ValueError, "category"):
            self.service.import_csv(csv_path)

        self.assertEqual(list(self.transactions.iter_all()), [])

    def test_rejects_non_utf8_csv(self) -> None:
        csv_path = self.data_dir / "invalid-encoding.csv"
        csv_path.write_bytes(b"date,type,category,amount\n\xff\n")

        with self.assertRaisesRegex(ValueError, "UTF-8"):
            self.service.import_csv(csv_path)


class ImportCliTest(unittest.TestCase):
    def test_import_command_reports_counts_and_imported_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            CategoryRepository(data_dir).append("food")
            csv_path = data_dir / "input.csv"
            csv_path.write_text(
                "date,type,category,amount,memo,tags\n"
                "2026-10-01,expense,food,15000,점심,meal\n"
                "invalid,expense,food,1000,오류,\n",
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "import",
                        "--from",
                        str(csv_path),
                    ]
                )

            result = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("[건너뜀] 3번째 줄", result)
            self.assertIn("[완료] imported=1, skipped=1", result)
            self.assertEqual(len(list(TransactionRepository(data_dir).iter_all())), 1)

    def test_import_command_reports_missing_file_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.csv"

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "import",
                        "--from",
                        str(missing_path),
                    ]
                )

            result = output.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn("CSV 파일을 찾을 수 없습니다", result)
            self.assertNotIn("Traceback", result)


if __name__ == "__main__":
    unittest.main()
