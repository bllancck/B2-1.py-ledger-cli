"""Tests for streaming transaction search filters."""

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


def make_transaction(
    *,
    date: str,
    transaction_type: str,
    category: str,
    memo: str,
    tags: list[str],
) -> Transaction:
    """Create a valid transaction for search assertions."""
    return Transaction(
        id=str(uuid4()),
        type=transaction_type,
        date=date,
        amount=1_000,
        category=category,
        memo=memo,
        tags=tags,
    )


class TransactionSearchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.data_dir = Path(self.temporary_directory.name)
        self.repository = TransactionRepository(self.data_dir)
        self.service = TransactionService(
            self.repository,
            CategoryRepository(self.data_dir),
        )
        self.first = make_transaction(
            date="2026-09-01",
            transaction_type="expense",
            category="food",
            memo="Morning Coffee",
            tags=["meal", "cafe"],
        )
        self.second = make_transaction(
            date="2026-10-10",
            transaction_type="income",
            category="salary",
            memo="October Salary",
            tags=["work"],
        )
        self.third = make_transaction(
            date="2026-10-20",
            transaction_type="expense",
            category="food",
            memo="Dinner",
            tags=["meal"],
        )
        for transaction in (self.first, self.second, self.third):
            self.repository.append(transaction)

    def test_each_filter_returns_latest_matching_transactions(self) -> None:
        cases = (
            ({"date_from": "2026-10-01"}, [self.third, self.second]),
            ({"date_to": "2026-09-30"}, [self.first]),
            ({"category": "food"}, [self.third, self.first]),
            ({"transaction_type": "income"}, [self.second]),
            ({"query": "coffee"}, [self.first]),
            ({"tag": "meal"}, [self.third, self.first]),
        )

        for filters, expected in cases:
            with self.subTest(filters=filters):
                self.assertEqual(
                    list(self.service.iter_search_transactions(**filters)),
                    expected,
                )

    def test_combined_filters_use_and_logic(self) -> None:
        result = list(
            self.service.iter_search_transactions(
                date_from="2026-10-01",
                date_to="2026-10-31",
                category="food",
                transaction_type="expense",
                tag="meal",
            )
        )

        self.assertEqual(result, [self.third])

    def test_reject_invalid_date_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "시작일"):
            list(
                self.service.iter_search_transactions(
                    date_from="2026-10-31",
                    date_to="2026-10-01",
                )
            )

    def test_search_generator_reads_records_lazily(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            repository = TransactionRepository(data_dir)
            repository.initialize()
            repository.path.write_text("not-json\n", encoding="utf-8")
            newest = make_transaction(
                date="2026-10-20",
                transaction_type="expense",
                category="food",
                memo="Newest",
                tags=[],
            )
            repository.append(newest)
            service = TransactionService(repository, CategoryRepository(data_dir))
            results = service.iter_search_transactions(query="newest")

            self.assertEqual(next(results), newest)
            with self.assertRaisesRegex(ValueError, "올바른 JSON"):
                next(results)


class TransactionSearchCliTest(unittest.TestCase):
    def test_search_command_prints_results_and_handles_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            transaction = make_transaction(
                date="2026-10-20",
                transaction_type="expense",
                category="food",
                memo="Dinner",
                tags=["meal"],
            )
            TransactionRepository(data_dir).append(transaction)

            with redirect_stdout(io.StringIO()) as output:
                success_code = main(
                    ["--data-dir", temporary_directory, "search", "--tag", "meal"]
                )
            self.assertEqual(success_code, 0)
            self.assertIn(transaction.id, output.getvalue())

            with redirect_stdout(io.StringIO()) as output:
                empty_code = main(
                    ["--data-dir", temporary_directory, "search", "--tag", "work"]
                )
            self.assertEqual(empty_code, 0)
            self.assertIn("검색 결과가 없습니다", output.getvalue())

    def test_search_command_reports_invalid_date(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with redirect_stdout(io.StringIO()) as output:
                exit_code = main(
                    [
                        "--data-dir",
                        temporary_directory,
                        "search",
                        "--from",
                        "2026-02-30",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("실제 달력에 존재하는 날짜", output.getvalue())


if __name__ == "__main__":
    unittest.main()
