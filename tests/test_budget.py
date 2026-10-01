"""Tests for monthly budget settings and summary integration."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from uuid import uuid4

from budget_app.budget_service import BudgetService
from budget_app.cli import main
from budget_app.models import Transaction
from budget_app.repository import BudgetRepository, TransactionRepository
from budget_app.summary_service import SummaryService


def make_expense(amount: int) -> Transaction:
    """Create one October expense for budget summary assertions."""
    return Transaction(
        id=str(uuid4()),
        type="expense",
        date="2026-10-01",
        amount=amount,
        category="food",
    )


class BudgetServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)
        self.repository = BudgetRepository(self.data_dir)
        self.service = BudgetService(self.repository)

    def test_set_budget_persists_across_repository_instances(self) -> None:
        self.service.set_budget("2026-10", 500_000)

        loaded = BudgetService(BudgetRepository(self.data_dir)).get_budget("2026-10")

        self.assertEqual(loaded, 500_000)

    def test_setting_same_month_replaces_previous_budget(self) -> None:
        self.service.set_budget("2026-10", 500_000)
        self.service.set_budget("2026-10", 600_000)

        self.assertEqual(list(self.repository.iter_all()), [("2026-10", 600_000)])

    def test_rejects_invalid_month_and_amount(self) -> None:
        invalid_inputs = (("2026-13", 500_000), ("2026-10", 0))

        for month, amount in invalid_inputs:
            with self.subTest(month=month, amount=amount):
                with self.assertRaises(ValueError):
                    self.service.set_budget(month, amount)


class BudgetSummaryTest(unittest.TestCase):
    def test_summary_calculates_budget_usage_within_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            TransactionRepository(data_dir).append(make_expense(250_000))
            BudgetRepository(data_dir).set("2026-10", 500_000)
            service = SummaryService(
                TransactionRepository(data_dir),
                BudgetRepository(data_dir),
            )

            summary = service.summarize_month("2026-10", top=3)

            assert summary is not None
            self.assertEqual(summary.budget, 500_000)
            self.assertEqual(summary.budget_usage_rate, 50.0)
            self.assertFalse(summary.is_budget_exceeded)
            self.assertEqual(summary.budget_overage, 0)

    def test_summary_reports_budget_overage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            TransactionRepository(data_dir).append(make_expense(600_000))
            BudgetRepository(data_dir).set("2026-10", 500_000)

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "summary",
                        "--month",
                        "2026-10",
                    ]
                )

            result = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("사용률 120.0%", result)
            self.assertIn("예산 상태: 초과", result)
            self.assertIn("예산을 100000원 초과", result)


class BudgetCliTest(unittest.TestCase):
    def test_budget_set_command_saves_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "budget",
                        "set",
                        "--month",
                        "2026-10",
                        "--amount",
                        "500000",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("[저장 완료] 2026-10 예산 500000원", output.getvalue())
            self.assertEqual(
                BudgetRepository(Path(temporary_directory)).get("2026-10"),
                500_000,
            )

    def test_budget_set_command_rejects_non_positive_amount(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "budget",
                        "set",
                        "--month",
                        "2026-10",
                        "--amount",
                        "0",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("금액은 0보다 큰 정수", output.getvalue())


if __name__ == "__main__":
    unittest.main()
