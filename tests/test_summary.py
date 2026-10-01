"""Tests for monthly transaction summaries."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from uuid import uuid4

from budget_app.cli import main
from budget_app.models import Transaction
from budget_app.repository import TransactionRepository
from budget_app.summary_service import SummaryService


def make_transaction(
    *,
    date: str,
    transaction_type: str,
    amount: int,
    category: str,
) -> Transaction:
    """Create a valid transaction for summary assertions."""
    return Transaction(
        id=str(uuid4()),
        type=transaction_type,
        date=date,
        amount=amount,
        category=category,
    )


class SummaryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)
        self.repository = TransactionRepository(self.data_dir)
        self.service = SummaryService(self.repository)

    def test_calculates_totals_balance_and_top_expense_categories(self) -> None:
        transactions = (
            make_transaction(
                date="2026-10-01",
                transaction_type="income",
                amount=3_000_000,
                category="salary",
            ),
            make_transaction(
                date="2026-10-03",
                transaction_type="expense",
                amount=25_000,
                category="food",
            ),
            make_transaction(
                date="2026-10-05",
                transaction_type="expense",
                amount=20_000,
                category="food",
            ),
            make_transaction(
                date="2026-10-10",
                transaction_type="expense",
                amount=150_000,
                category="rent",
            ),
            make_transaction(
                date="2026-10-11",
                transaction_type="expense",
                amount=20_000,
                category="transport",
            ),
            make_transaction(
                date="2026-09-30",
                transaction_type="expense",
                amount=999_999,
                category="other-month",
            ),
        )
        for transaction in transactions:
            self.repository.append(transaction)

        summary = self.service.summarize_month("2026-10", top=2)

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary.total_income, 3_000_000)
        self.assertEqual(summary.total_expense, 215_000)
        self.assertEqual(summary.balance, 2_785_000)
        self.assertEqual(
            summary.top_expense_categories,
            [("rent", 150_000), ("food", 45_000)],
        )

    def test_sorts_equal_expense_totals_by_category_name(self) -> None:
        for category in ("transport", "food"):
            self.repository.append(
                make_transaction(
                    date="2026-10-01",
                    transaction_type="expense",
                    amount=10_000,
                    category=category,
                )
            )

        summary = self.service.summarize_month("2026-10", top=2)

        assert summary is not None
        self.assertEqual(
            summary.top_expense_categories,
            [("food", 10_000), ("transport", 10_000)],
        )

    def test_returns_income_only_summary_without_expense_categories(self) -> None:
        self.repository.append(
            make_transaction(
                date="2026-10-01",
                transaction_type="income",
                amount=100_000,
                category="salary",
            )
        )

        summary = self.service.summarize_month("2026-10", top=3)

        assert summary is not None
        self.assertEqual(summary.total_expense, 0)
        self.assertEqual(summary.top_expense_categories, [])

    def test_returns_none_when_month_has_no_transactions(self) -> None:
        self.assertIsNone(self.service.summarize_month("2026-10", top=3))

    def test_rejects_invalid_month_and_top(self) -> None:
        invalid_inputs = (("2026-13", 3), ("2026-10", 0))

        for month, top in invalid_inputs:
            with self.subTest(month=month, top=top):
                with self.assertRaises(ValueError):
                    self.service.summarize_month(month, top)


class SummaryCliTest(unittest.TestCase):
    def test_summary_command_prints_calculated_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = TransactionRepository(Path(temporary_directory))
            repository.append(
                make_transaction(
                    date="2026-10-01",
                    transaction_type="income",
                    amount=100_000,
                    category="salary",
                )
            )
            repository.append(
                make_transaction(
                    date="2026-10-02",
                    transaction_type="expense",
                    amount=30_000,
                    category="food",
                )
            )

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "summary",
                        "--month",
                        "2026-10",
                        "--top",
                        "1",
                    ]
                )

            result = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("총 수입: 100000원", result)
            self.assertIn("총 지출: 30000원", result)
            self.assertIn("잔액: 70000원", result)
            self.assertIn("1) food 30000원", result)

    def test_summary_command_handles_empty_month_and_invalid_top(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with redirect_stdout(io.StringIO()) as output:
                empty_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "summary",
                        "--month",
                        "2026-10",
                    ]
                )
            self.assertEqual(empty_code, 0)
            self.assertIn("데이터 없음: 2026-10", output.getvalue())

            with redirect_stdout(io.StringIO()) as output:
                invalid_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "summary",
                        "--month",
                        "2026-10",
                        "--top",
                        "0",
                    ]
                )
            self.assertEqual(invalid_code, 1)
            self.assertIn("상위 카테고리 수", output.getvalue())


if __name__ == "__main__":
    unittest.main()
