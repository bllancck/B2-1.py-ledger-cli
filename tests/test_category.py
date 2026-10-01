"""Tests for category management rules and CLI commands."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from budget_app.cli import main
from budget_app.models import Transaction
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.category_service import CategoryService


class CategoryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)
        self.categories = CategoryRepository(self.data_dir)
        self.transactions = TransactionRepository(self.data_dir)
        self.service = CategoryService(self.categories, self.transactions)

    def test_add_and_list_categories(self) -> None:
        self.service.add_category(" food ")
        self.service.add_category("transport")

        self.assertEqual(self.service.list_categories(), ["food", "transport"])

    def test_reject_duplicate_category(self) -> None:
        self.service.add_category("food")

        with self.assertRaisesRegex(ValueError, "이미 등록된 카테고리"):
            self.service.add_category("food")

        self.assertEqual(self.service.list_categories(), ["food"])

    def test_remove_unused_category(self) -> None:
        self.service.add_category("food")

        removed = self.service.remove_category("food")

        self.assertEqual(removed, "food")
        self.assertEqual(self.service.list_categories(), [])

    def test_reject_removing_unknown_category(self) -> None:
        with self.assertRaisesRegex(ValueError, "등록되지 않은 카테고리"):
            self.service.remove_category("food")

    def test_reject_removing_category_used_by_transaction(self) -> None:
        self.service.add_category("food")
        self.transactions.append(
            Transaction(
                id=str(uuid4()),
                type="expense",
                date="2026-10-01",
                amount=15_000,
                category="food",
            )
        )

        with self.assertRaisesRegex(ValueError, "사용 중인 카테고리"):
            self.service.remove_category("food")

        self.assertEqual(self.service.list_categories(), ["food"])


class CategoryCliTest(unittest.TestCase):
    def test_add_list_and_remove_category_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            arguments = ["--data-dir", temporary_directory, "category"]

            with patch("builtins.input", return_value="food"):
                with redirect_stdout(io.StringIO()) as output:
                    add_exit_code = main([*arguments, "add"])
            self.assertEqual(add_exit_code, 0)
            self.assertIn("[저장 완료] category=food", output.getvalue())

            with redirect_stdout(io.StringIO()) as output:
                list_exit_code = main([*arguments, "list"])
            self.assertEqual(list_exit_code, 0)
            self.assertIn("- food", output.getvalue())

            with patch("builtins.input", return_value="food"):
                with redirect_stdout(io.StringIO()) as output:
                    remove_exit_code = main([*arguments, "remove"])
            self.assertEqual(remove_exit_code, 0)
            self.assertIn("[삭제 완료] category=food", output.getvalue())

    def test_duplicate_category_returns_nonzero_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            arguments = ["--data-dir", temporary_directory, "category", "add"]

            with patch("builtins.input", return_value="food"):
                with redirect_stdout(io.StringIO()):
                    main(arguments)

            with patch("builtins.input", return_value="food"):
                with redirect_stdout(io.StringIO()) as output:
                    exit_code = main(arguments)

            self.assertEqual(exit_code, 1)
            self.assertIn("[오류] 이미 등록된 카테고리", output.getvalue())


if __name__ == "__main__":
    unittest.main()
