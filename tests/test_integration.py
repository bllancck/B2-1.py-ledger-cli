"""End-to-end tests for the complete ledger CLI workflow."""

import io
import tempfile
import unittest
from contextlib import nullcontext, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from budget_app.cli import main
from budget_app.repository import (
    BUDGETS_FILENAME,
    CATEGORIES_FILENAME,
    TRANSACTIONS_FILENAME,
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)


class LedgerWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)

    def run_cli(
        self,
        *arguments: str,
        user_input: list[str] | None = None,
    ) -> tuple[int, str]:
        """Run one CLI command against the shared integration data directory."""
        input_context = (
            patch("builtins.input", side_effect=user_input)
            if user_input is not None
            else nullcontext()
        )
        with input_context:
            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    ["--data-dir", str(self.data_dir), *arguments]
                )
        return exit_code, output.getvalue()

    def add_category(self, name: str) -> None:
        """Register one category through the CLI."""
        exit_code, output = self.run_cli("category", "add", user_input=[name])
        self.assertEqual(exit_code, 0)
        self.assertIn(f"category={name}", output)

    def add_transaction(self, values: list[str]) -> None:
        """Add one transaction through the interactive CLI."""
        exit_code, output = self.run_cli("add", user_input=values)
        self.assertEqual(exit_code, 0)
        self.assertIn("[저장 완료] id=", output)

    def test_complete_user_workflow_shares_persistent_data(self) -> None:
        for category in ("salary", "food", "transport"):
            self.add_category(category)

        category_code, category_output = self.run_cli("category", "list")
        self.assertEqual(category_code, 0)
        for category in ("salary", "food", "transport"):
            self.assertIn(f"- {category}", category_output)

        self.add_transaction(
            ["2026-10-01", "income", "salary", "3000000", "급여", "work"]
        )
        self.add_transaction(
            ["2026-10-02", "expense", "food", "250000", "식비", "meal"]
        )
        self.add_transaction(
            ["2026-10-03", "expense", "transport", "50000", "교통", "commute"]
        )

        stored = list(TransactionRepository(self.data_dir).iter_all())
        self.assertEqual(len(stored), 3)
        food_id = next(item.id for item in stored if item.category == "food")
        transport_id = next(item.id for item in stored if item.category == "transport")

        list_code, list_output = self.run_cli("list", "--limit", "3")
        self.assertEqual(list_code, 0)
        self.assertLess(list_output.index(transport_id), list_output.index(food_id))

        search_code, search_output = self.run_cli(
            "search",
            "--from",
            "2026-10-01",
            "--to",
            "2026-10-31",
            "--type",
            "expense",
        )
        self.assertEqual(search_code, 0)
        self.assertIn(food_id, search_output)
        self.assertIn(transport_id, search_output)
        self.assertNotIn("salary", search_output)

        update_code, update_output = self.run_cli(
            "update",
            "--id",
            food_id,
            "--amount",
            "300000",
            "--memo",
            "수정된 식비",
            "--tags",
            "meal,updated",
        )
        self.assertEqual(update_code, 0)
        self.assertIn("[수정 완료]", update_output)

        delete_code, delete_output = self.run_cli(
            "delete",
            "--id",
            transport_id,
        )
        self.assertEqual(delete_code, 0)
        self.assertIn("[삭제 완료]", delete_output)

        budget_code, budget_output = self.run_cli(
            "budget",
            "set",
            "--month",
            "2026-10",
            "--amount",
            "200000",
        )
        self.assertEqual(budget_code, 0)
        self.assertIn("예산 200000원", budget_output)

        summary_code, summary_output = self.run_cli(
            "summary",
            "--month",
            "2026-10",
        )
        self.assertEqual(summary_code, 0)
        self.assertIn("총 수입: 3000000원", summary_output)
        self.assertIn("총 지출: 300000원", summary_output)
        self.assertIn("잔액: 2700000원", summary_output)
        self.assertIn("사용률 150.0%", summary_output)
        self.assertIn("예산을 100000원 초과", summary_output)

        export_path = self.data_dir / "october.csv"
        export_code, export_output = self.run_cli(
            "export",
            "--out",
            str(export_path),
            "--month",
            "2026-10",
        )
        self.assertEqual(export_code, 0)
        self.assertIn("(2 records)", export_output)
        self.assertTrue(export_path.is_file())

        import_code, import_output = self.run_cli(
            "import",
            "--from",
            str(export_path),
        )
        self.assertEqual(import_code, 0)
        self.assertIn("imported=2, skipped=0", import_output)

        reloaded_transactions = list(
            TransactionRepository(self.data_dir).iter_all()
        )
        self.assertEqual(len(reloaded_transactions), 4)
        self.assertEqual(len({item.id for item in reloaded_transactions}), 4)
        self.assertEqual(
            next(CategoryRepository(self.data_dir).iter_all()),
            "salary",
        )
        self.assertEqual(BudgetRepository(self.data_dir).get("2026-10"), 200_000)
        for filename in (
            TRANSACTIONS_FILENAME,
            CATEGORIES_FILENAME,
            BUDGETS_FILENAME,
        ):
            self.assertTrue((self.data_dir / filename).is_file())

    def test_invalid_inputs_remain_controlled_in_shared_workflow(self) -> None:
        self.add_category("food")
        self.add_transaction(
            ["2026-10-01", "expense", "food", "15000", "점심", "meal"]
        )
        transaction = next(TransactionRepository(self.data_dir).iter_all())

        error_commands = (
            ("search", "--from", "2026-02-30"),
            ("budget", "set", "--month", "2026-10", "--amount", "0"),
            ("update", "--id", transaction.id, "--category", "unknown"),
            ("delete", "--id", str(uuid4())),
        )
        for arguments in error_commands:
            with self.subTest(arguments=arguments):
                exit_code, output = self.run_cli(*arguments)
                self.assertEqual(exit_code, 1)
                self.assertIn("[오류]", output)
                self.assertIn("[힌트]", output)
                self.assertNotIn("Traceback", output)

        summary_code, summary_output = self.run_cli(
            "summary",
            "--month",
            "2026-12",
        )
        self.assertEqual(summary_code, 0)
        self.assertIn("데이터 없음: 2026-12", summary_output)

        invalid_csv = self.data_dir / "invalid.csv"
        invalid_csv.write_text(
            "date,type,amount\n2026-10-01,expense,1000\n",
            encoding="utf-8",
        )
        import_code, import_output = self.run_cli(
            "import",
            "--from",
            str(invalid_csv),
        )
        self.assertEqual(import_code, 1)
        self.assertIn("CSV 필수 헤더", import_output)
        self.assertIn("[힌트]", import_output)
        self.assertNotIn("Traceback", import_output)
        self.assertEqual(len(list(TransactionRepository(self.data_dir).iter_all())), 1)


if __name__ == "__main__":
    unittest.main()
