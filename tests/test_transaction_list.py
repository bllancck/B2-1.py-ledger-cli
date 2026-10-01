"""Tests for latest-first streaming transaction lists."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from uuid import uuid4

from budget_app.cli import main
from budget_app.models import Transaction
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.transaction_service import TransactionService


def make_transaction(memo: str) -> Transaction:
    """Create a valid transaction identified by its memo in assertions."""
    return Transaction(
        id=str(uuid4()),
        type="expense",
        date="2026-10-01",
        amount=1_000,
        category="food",
        memo=memo,
    )


class TransactionListServiceTest(unittest.TestCase):
    def test_iter_latest_transactions_uses_append_order_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            repository = TransactionRepository(data_dir)
            transactions = [
                make_transaction("first"),
                make_transaction("second"),
                make_transaction("third"),
            ]
            for transaction in transactions:
                repository.append(transaction)
            service = TransactionService(repository, CategoryRepository(data_dir))

            latest = list(service.iter_latest_transactions(2))

            self.assertEqual(latest, [transactions[2], transactions[1]])

    def test_reject_non_positive_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            service = TransactionService(
                TransactionRepository(data_dir),
                CategoryRepository(data_dir),
            )

            with self.assertRaisesRegex(ValueError, "0보다 큰 정수"):
                service.iter_latest_transactions(0)

    def test_limit_stops_before_reading_older_invalid_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            repository = TransactionRepository(data_dir)
            repository.initialize()
            repository.path.write_text("not-json\n", encoding="utf-8")
            newest = make_transaction("newest")
            repository.append(newest)
            service = TransactionService(repository, CategoryRepository(data_dir))

            latest = list(service.iter_latest_transactions(1))

            self.assertEqual(latest, [newest])
            with self.assertRaisesRegex(ValueError, "올바른 JSON"):
                list(service.iter_latest_transactions(2))


class TransactionListCliTest(unittest.TestCase):
    def test_list_command_prints_latest_transactions_up_to_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            repository = TransactionRepository(data_dir)
            transactions = [
                make_transaction("first"),
                make_transaction("second"),
                make_transaction("third"),
            ]
            for transaction in transactions:
                repository.append(transaction)

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    ["--data-dir", temporary_directory, "list", "--limit", "2"]
                )

            result = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertLess(result.index(transactions[2].id), result.index(transactions[1].id))
            self.assertNotIn(transactions[0].id, result)

    def test_list_command_handles_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(["--data-dir", temporary_directory, "list"])

            self.assertEqual(exit_code, 0)
            self.assertIn("저장된 거래가 없습니다", output.getvalue())

    def test_list_command_rejects_non_positive_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    ["--data-dir", temporary_directory, "list", "--limit", "0"]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("조회 건수는 0보다 큰 정수", output.getvalue())


if __name__ == "__main__":
    unittest.main()
