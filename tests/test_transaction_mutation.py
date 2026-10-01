"""Tests for transaction update and delete operations."""

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


class TransactionMutationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)
        self.categories = CategoryRepository(self.data_dir)
        self.categories.append("food")
        self.categories.append("transport")
        self.transactions = TransactionRepository(self.data_dir)
        self.first = Transaction(
            id=str(uuid4()),
            type="expense",
            date="2026-10-01",
            amount=15_000,
            category="food",
            memo="점심",
            tags=["meal"],
        )
        self.second = Transaction(
            id=str(uuid4()),
            type="expense",
            date="2026-10-02",
            amount=2_000,
            category="transport",
        )
        self.transactions.append(self.first)
        self.transactions.append(self.second)
        self.service = TransactionService(self.transactions, self.categories)

    def test_update_selected_fields_and_preserve_order(self) -> None:
        updated = self.service.update_transaction(
            self.first.id,
            date="2026-10-03",
            category="transport",
            amount=20_000,
            memo="",
            tags=[],
        )

        stored = list(self.transactions.iter_all())
        self.assertEqual(updated.id, self.first.id)
        self.assertEqual(updated.type, "expense")
        self.assertEqual(updated.date, "2026-10-03")
        self.assertEqual(updated.category, "transport")
        self.assertEqual(updated.amount, 20_000)
        self.assertEqual(updated.memo, "")
        self.assertEqual(updated.tags, [])
        self.assertEqual(stored, [updated, self.second])

    def test_reject_invalid_update_without_changing_file(self) -> None:
        before = self.transactions.path.read_text(encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "등록되지 않은 카테고리"):
            self.service.update_transaction(self.first.id, category="unknown")

        self.assertEqual(
            self.transactions.path.read_text(encoding="utf-8"),
            before,
        )

    def test_reject_update_without_fields_or_unknown_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "수정할 필드"):
            self.service.update_transaction(self.first.id)

        with self.assertRaisesRegex(ValueError, "거래가 없습니다"):
            self.service.update_transaction(str(uuid4()), amount=1_000)

    def test_delete_transaction_and_keep_other_records(self) -> None:
        deleted = self.service.delete_transaction(self.first.id)

        self.assertEqual(deleted, self.first)
        self.assertEqual(list(self.transactions.iter_all()), [self.second])

    def test_reject_deleting_unknown_id_without_changing_file(self) -> None:
        before = self.transactions.path.read_text(encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "거래가 없습니다"):
            self.service.delete_transaction(str(uuid4()))

        self.assertEqual(
            self.transactions.path.read_text(encoding="utf-8"),
            before,
        )


class TransactionMutationCliTest(unittest.TestCase):
    def test_update_and_delete_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            categories = CategoryRepository(data_dir)
            categories.append("food")
            categories.append("transport")
            transactions = TransactionRepository(data_dir)
            transaction = Transaction(
                id=str(uuid4()),
                type="expense",
                date="2026-10-01",
                amount=15_000,
                category="food",
                memo="점심",
                tags=["meal"],
            )
            transactions.append(transaction)

            with redirect_stdout(io.StringIO()) as output:
                update_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "update",
                        "--id",
                        transaction.id,
                        "--category",
                        "transport",
                        "--amount",
                        "20000",
                        "--memo",
                        "",
                        "--tags",
                        "",
                    ]
                )
            self.assertEqual(update_code, 0)
            self.assertIn("[수정 완료]", output.getvalue())
            updated = list(transactions.iter_all())[0]
            self.assertEqual(updated.category, "transport")
            self.assertEqual(updated.amount, 20_000)
            self.assertEqual(updated.memo, "")
            self.assertEqual(updated.tags, [])

            with redirect_stdout(io.StringIO()) as output:
                delete_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "delete",
                        "--id",
                        transaction.id,
                    ]
                )
            self.assertEqual(delete_code, 0)
            self.assertIn("[삭제 완료]", output.getvalue())
            self.assertEqual(list(transactions.iter_all()), [])

    def test_unknown_id_returns_nonzero_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            unknown_id = str(uuid4())

            with redirect_stdout(io.StringIO()) as output:
                update_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "update",
                        "--id",
                        unknown_id,
                        "--amount",
                        "1000",
                    ]
                )
            self.assertEqual(update_code, 1)
            self.assertIn("거래가 없습니다", output.getvalue())

            with redirect_stdout(io.StringIO()) as output:
                delete_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "delete",
                        "--id",
                        unknown_id,
                    ]
                )
            self.assertEqual(delete_code, 1)
            self.assertIn("거래가 없습니다", output.getvalue())


if __name__ == "__main__":
    unittest.main()
