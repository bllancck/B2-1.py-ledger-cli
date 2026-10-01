"""Tests for JSONL file initialization and persistence."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from uuid import uuid4

from budget_app.cli import main
from budget_app.models import Transaction
from budget_app.repository import (
    BUDGETS_FILENAME,
    CATEGORIES_FILENAME,
    TRANSACTIONS_FILENAME,
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
    initialize_data_files,
)


class RepositoryTest(unittest.TestCase):
    def test_initialize_creates_three_empty_data_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "ledger-data"

            initialize_data_files(data_dir)

            for filename in (
                TRANSACTIONS_FILENAME,
                CATEGORIES_FILENAME,
                BUDGETS_FILENAME,
            ):
                data_file = data_dir / filename
                self.assertTrue(data_file.is_file())
                self.assertEqual(data_file.read_text(encoding="utf-8"), "")

    def test_initialize_preserves_existing_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            transactions_file = data_dir / TRANSACTIONS_FILENAME
            transactions_file.write_text('{"existing": true}\n', encoding="utf-8")

            initialize_data_files(data_dir)

            self.assertEqual(
                transactions_file.read_text(encoding="utf-8"),
                '{"existing": true}\n',
            )

    def test_transaction_remains_available_from_new_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            transaction = Transaction(
                id=str(uuid4()),
                type="expense",
                date="2026-10-01",
                amount=15_000,
                category="식비",
                memo="점심",
                tags=["meal"],
            )
            TransactionRepository(data_dir).append(transaction)

            loaded = list(TransactionRepository(data_dir).iter_all())

            self.assertEqual(loaded, [transaction])

    def test_category_remains_available_from_new_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            CategoryRepository(data_dir).append("식비")

            loaded = list(CategoryRepository(data_dir).iter_all())

            self.assertEqual(loaded, ["식비"])

    def test_budget_remains_available_from_new_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            BudgetRepository(data_dir).append("2026-10", 500_000)

            loaded = list(BudgetRepository(data_dir).iter_all())

            self.assertEqual(loaded, [("2026-10", 500_000)])

    def test_cli_uses_custom_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "custom-data"

            with redirect_stdout(io.StringIO()):
                exit_code = main(["--data-dir", str(data_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((data_dir / TRANSACTIONS_FILENAME).is_file())
            self.assertTrue((data_dir / CATEGORIES_FILENAME).is_file())
            self.assertTrue((data_dir / BUDGETS_FILENAME).is_file())


if __name__ == "__main__":
    unittest.main()
