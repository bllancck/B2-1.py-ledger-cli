"""Tests for the transaction model and its validation rules."""

import unittest
from typing import Any
from uuid import uuid4

from budget_app.models import Transaction
from budget_app.validation import validate_registered_category


def make_transaction(**changes: Any) -> Transaction:
    """Create a valid transaction with selected field overrides."""
    values: dict[str, Any] = {
        "id": str(uuid4()),
        "type": "expense",
        "date": "2026-10-01",
        "amount": 15_000,
        "category": "food",
        "memo": "점심",
        "tags": ["meal"],
    }
    values.update(changes)
    return Transaction(**values)


class TransactionTest(unittest.TestCase):
    def test_create_transaction_with_valid_values(self) -> None:
        transaction = make_transaction()

        self.assertEqual(transaction.type, "expense")
        self.assertEqual(transaction.amount, 15_000)
        self.assertEqual(transaction.tags, ["meal"])

    def test_optional_fields_use_independent_empty_defaults(self) -> None:
        first = Transaction(
            id=str(uuid4()),
            type="expense",
            date="2026-10-01",
            amount=15_000,
            category="food",
        )
        second = Transaction(
            id=str(uuid4()),
            type="expense",
            date="2026-10-01",
            amount=15_000,
            category="food",
        )

        first.tags.append("first")

        self.assertEqual(second.memo, "")
        self.assertEqual(second.tags, [])

    def test_reject_invalid_transaction_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "UUID"):
            make_transaction(id="TX-1")

    def test_reject_invalid_transaction_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "income 또는 expense"):
            make_transaction(type="transfer")

    def test_reject_invalid_date_format_and_nonexistent_date(self) -> None:
        invalid_dates = ("2026-1-01", "2026-02-30")

        for invalid_date in invalid_dates:
            with self.subTest(date=invalid_date):
                with self.assertRaises(ValueError):
                    make_transaction(date=invalid_date)

    def test_reject_non_positive_or_non_integer_amount(self) -> None:
        invalid_amounts = (0, -1, 1.5, True)

        for invalid_amount in invalid_amounts:
            with self.subTest(amount=invalid_amount):
                with self.assertRaisesRegex(ValueError, "0보다 큰 정수"):
                    make_transaction(amount=invalid_amount)

    def test_reject_empty_category(self) -> None:
        with self.assertRaisesRegex(ValueError, "비어 있을 수 없습니다"):
            make_transaction(category="   ")

    def test_check_category_against_registered_categories(self) -> None:
        validate_registered_category("food", {"food", "transport"})

        with self.assertRaisesRegex(ValueError, "등록되지 않은 카테고리"):
            validate_registered_category("travel", {"food", "transport"})

    def test_reject_invalid_memo_or_tags(self) -> None:
        with self.assertRaisesRegex(ValueError, "메모는 문자열"):
            make_transaction(memo=None)

        with self.assertRaisesRegex(ValueError, "태그는 문자열 목록"):
            make_transaction(tags="meal")

        with self.assertRaisesRegex(ValueError, "비어 있지 않은 문자열"):
            make_transaction(tags=[""])


if __name__ == "__main__":
    unittest.main()
