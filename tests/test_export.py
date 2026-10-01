"""Tests for filtered transaction CSV exports."""

import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from uuid import uuid4

from budget_app.cli import main
from budget_app.export_service import CSV_COLUMNS, ExportService
from budget_app.import_service import ImportService
from budget_app.models import Transaction
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.transaction_service import TransactionService


def make_transaction(
    date: str,
    memo: str,
    *,
    tags: list[str] | None = None,
) -> Transaction:
    """Create one transaction identified by its date and memo."""
    return Transaction(
        id=str(uuid4()),
        type="expense",
        date=date,
        amount=15_000,
        category="food",
        memo=memo,
        tags=list(tags) if tags is not None else [],
    )


class ExportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)
        self.repository = TransactionRepository(self.data_dir)
        self.transactions = (
            make_transaction("2026-09-30", "September"),
            make_transaction("2026-10-01", "October first", tags=["meal", "lunch"]),
            make_transaction("2026-10-31", "October last"),
            make_transaction("2026-11-01", "November"),
        )
        for transaction in self.transactions:
            self.repository.append(transaction)
        self.service = ExportService(
            TransactionService(
                self.repository,
                CategoryRepository(self.data_dir),
            )
        )

    def read_rows(self, output_path: Path) -> list[dict[str, str]]:
        """Read an exported CSV fixture as dictionaries."""
        with output_path.open("r", encoding="utf-8", newline="") as csv_file:
            return list(csv.DictReader(csv_file))

    def test_exports_only_requested_month_with_shared_schema(self) -> None:
        output_path = self.data_dir / "october.csv"

        exported = self.service.export_csv(output_path, month="2026-10")
        rows = self.read_rows(output_path)

        self.assertEqual(exported, 2)
        self.assertEqual(tuple(rows[0]), CSV_COLUMNS)
        self.assertEqual(
            [row["memo"] for row in rows],
            ["October last", "October first"],
        )
        self.assertEqual(rows[1]["tags"], "meal,lunch")

    def test_exports_inclusive_date_range(self) -> None:
        output_path = self.data_dir / "range.csv"

        exported = self.service.export_csv(
            output_path,
            date_from="2026-10-31",
            date_to="2026-11-01",
        )

        self.assertEqual(exported, 2)
        self.assertEqual(
            [row["date"] for row in self.read_rows(output_path)],
            ["2026-11-01", "2026-10-31"],
        )

    def test_allows_one_sided_date_range(self) -> None:
        output_path = self.data_dir / "from.csv"

        exported = self.service.export_csv(
            output_path,
            date_from="2026-11-01",
        )

        self.assertEqual(exported, 1)
        self.assertEqual(self.read_rows(output_path)[0]["memo"], "November")

    def test_empty_result_creates_header_only_csv(self) -> None:
        output_path = self.data_dir / "empty.csv"

        exported = self.service.export_csv(output_path, month="2026-12")

        self.assertEqual(exported, 0)
        self.assertEqual(self.read_rows(output_path), [])
        self.assertEqual(
            output_path.read_text(encoding="utf-8").strip(),
            ",".join(CSV_COLUMNS),
        )

    def test_rejects_missing_conflicting_or_invalid_period(self) -> None:
        invalid_options = (
            {},
            {"month": "2026-10", "date_from": "2026-10-01"},
            {"month": "2026-13"},
            {"date_from": "2026-11-01", "date_to": "2026-10-01"},
        )

        for index, options in enumerate(invalid_options):
            with self.subTest(options=options):
                output_path = self.data_dir / f"invalid-{index}.csv"
                with self.assertRaises(ValueError):
                    self.service.export_csv(output_path, **options)
                self.assertFalse(output_path.exists())

    def test_exported_csv_can_be_imported(self) -> None:
        output_path = self.data_dir / "round-trip.csv"
        self.service.export_csv(output_path, month="2026-10")

        with tempfile.TemporaryDirectory() as import_directory:
            import_data_dir = Path(import_directory)
            categories = CategoryRepository(import_data_dir)
            categories.append("food")
            imported_repository = TransactionRepository(import_data_dir)
            result = ImportService(
                TransactionService(imported_repository, categories)
            ).import_csv(output_path)
            imported = list(imported_repository.iter_all())

        self.assertEqual(result.imported, 2)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(imported[1].tags, ["meal", "lunch"])


class ExportCliTest(unittest.TestCase):
    def test_export_command_reports_output_path_and_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            TransactionRepository(data_dir).append(
                make_transaction("2026-10-01", "exported")
            )
            output_path = data_dir / "output.csv"

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "export",
                        "--out",
                        str(output_path),
                        "--month",
                        "2026-10",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.is_file())
            self.assertIn(f"[완료] {output_path} (1 records)", output.getvalue())

    def test_export_command_rejects_missing_period(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "output.csv"

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "export",
                        "--out",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("기간 조건이 필요", output.getvalue())
            self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
