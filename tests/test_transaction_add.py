"""Tests for transaction creation service and interactive add command."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from budget_app.cli import main
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.services import TransactionService


class TransactionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)
        self.categories = CategoryRepository(self.data_dir)
        self.transactions = TransactionRepository(self.data_dir)
        self.service = TransactionService(self.transactions, self.categories)

    def test_add_transaction_persists_unique_ids(self) -> None:
        self.categories.append("salary")

        first = self.service.add_transaction(
            transaction_type="income",
            date="2026-10-01",
            amount=3_000_000,
            category="salary",
        )
        second = self.service.add_transaction(
            transaction_type="income",
            date="2026-10-02",
            amount=10_000,
            category="salary",
            memo="보너스",
            tags=["extra"],
        )

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(list(self.transactions.iter_all()), [first, second])

    def test_reject_unregistered_category_without_saving(self) -> None:
        with self.assertRaisesRegex(ValueError, "등록되지 않은 카테고리"):
            self.service.add_transaction(
                transaction_type="expense",
                date="2026-10-01",
                amount=15_000,
                category="food",
            )

        self.assertEqual(list(self.transactions.iter_all()), [])


class TransactionAddCliTest(unittest.TestCase):
    def test_reject_add_when_no_category_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(["--data-dir", temporary_directory, "add"])

            self.assertEqual(exit_code, 1)
            self.assertIn("등록된 카테고리가 없습니다", output.getvalue())
            self.assertEqual(
                list(TransactionRepository(Path(temporary_directory)).iter_all()),
                [],
            )

    def test_add_command_saves_all_input_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            CategoryRepository(data_dir).append("food")
            user_input = [
                "2026-10-01",
                "expense",
                "food",
                "15000",
                "점심",
                "meal, lunch",
            ]

            with patch("builtins.input", side_effect=user_input):
                with redirect_stdout(io.StringIO()) as output:
                    exit_code = main(["--data-dir", temporary_directory, "add"])

            saved = list(TransactionRepository(data_dir).iter_all())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].date, "2026-10-01")
            self.assertEqual(saved[0].type, "expense")
            self.assertEqual(saved[0].category, "food")
            self.assertEqual(saved[0].amount, 15_000)
            self.assertEqual(saved[0].memo, "점심")
            self.assertEqual(saved[0].tags, ["meal", "lunch"])
            self.assertIn(f"[저장 완료] id={saved[0].id}", output.getvalue())

    def test_add_command_reprompts_for_invalid_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            CategoryRepository(data_dir).append("food")
            user_input = [
                "2026-02-30",
                "2026-10-01",
                "transfer",
                "expense",
                "unknown",
                "food",
                "0",
                "15000",
                "",
                "",
            ]

            with patch("builtins.input", side_effect=user_input):
                with redirect_stdout(io.StringIO()) as output:
                    exit_code = main(["--data-dir", temporary_directory, "add"])

            saved = list(TransactionRepository(data_dir).iter_all())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(saved), 1)
            self.assertEqual(output.getvalue().count("[오류]"), 4)


if __name__ == "__main__":
    unittest.main()
