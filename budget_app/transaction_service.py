"""Apply business rules for transaction operations."""

from collections.abc import Iterator
from itertools import islice
from uuid import uuid4

from budget_app.models import Transaction, TransactionType
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.validation import (
    validate_category_name,
    validate_date,
    validate_limit,
    validate_registered_category,
    validate_tags,
    validate_transaction_id,
    validate_transaction_type,
)


class TransactionService:
    """Create, query, update, and delete validated transactions."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self._transactions = transaction_repository
        self._categories = category_repository

    def add_transaction(
        self,
        *,
        transaction_type: TransactionType,
        date: str,
        amount: int,
        category: str,
        memo: str = "",
        tags: list[str] | None = None,
    ) -> Transaction:
        """Validate, create, and persist one transaction."""
        validate_registered_category(category, self._categories.iter_all())
        transaction = Transaction(
            id=str(uuid4()),
            type=transaction_type,
            date=date,
            amount=amount,
            category=category,
            memo=memo,
            tags=list(tags) if tags is not None else [],
        )
        self._transactions.append(transaction)
        return transaction

    def iter_latest_transactions(self, limit: int) -> Iterator[Transaction]:
        """Yield at most limit transactions in latest-added order."""
        validate_limit(limit)
        return islice(self._transactions.iter_latest(), limit)

    def iter_search_transactions(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        transaction_type: TransactionType | None = None,
        query: str | None = None,
        tag: str | None = None,
    ) -> Iterator[Transaction]:
        """Yield latest-first transactions matching all supplied filters."""
        if date_from is not None:
            validate_date(date_from)
        if date_to is not None:
            validate_date(date_to)
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")
        if category is not None:
            validate_category_name(category)
            category = category.strip()
        if transaction_type is not None:
            validate_transaction_type(transaction_type)
        if query is not None and not query.strip():
            raise ValueError("메모 검색어는 비어 있을 수 없습니다.")
        if tag is not None:
            tag = tag.strip()
            validate_tags([tag])

        normalized_query = query.strip().casefold() if query is not None else None
        for transaction in self._transactions.iter_latest():
            if date_from is not None and transaction.date < date_from:
                continue
            if date_to is not None and transaction.date > date_to:
                continue
            if category is not None and transaction.category != category:
                continue
            if transaction_type is not None and transaction.type != transaction_type:
                continue
            if (
                normalized_query is not None
                and normalized_query not in transaction.memo.casefold()
            ):
                continue
            if tag is not None and tag not in transaction.tags:
                continue
            yield transaction

    def update_transaction(
        self,
        transaction_id: str,
        *,
        date: str | None = None,
        transaction_type: TransactionType | None = None,
        category: str | None = None,
        amount: int | None = None,
        memo: str | None = None,
        tags: list[str] | None = None,
    ) -> Transaction:
        """Update selected fields of one transaction and persist the result."""
        validate_transaction_id(transaction_id)
        if all(
            value is None
            for value in (date, transaction_type, category, amount, memo, tags)
        ):
            raise ValueError("수정할 필드를 하나 이상 지정해야 합니다.")

        transactions = list(self._transactions.iter_all())
        transaction_index = next(
            (
                index
                for index, transaction in enumerate(transactions)
                if transaction.id == transaction_id
            ),
            None,
        )
        if transaction_index is None:
            raise ValueError(f"해당 ID의 거래가 없습니다: {transaction_id}")

        current = transactions[transaction_index]
        if category is not None:
            category = category.strip()
            validate_registered_category(category, self._categories.iter_all())

        updated = Transaction(
            id=current.id,
            type=transaction_type if transaction_type is not None else current.type,
            date=date if date is not None else current.date,
            amount=amount if amount is not None else current.amount,
            category=category if category is not None else current.category,
            memo=memo if memo is not None else current.memo,
            tags=list(tags) if tags is not None else list(current.tags),
        )
        transactions[transaction_index] = updated
        self._transactions.replace_all(transactions)
        return updated

    def delete_transaction(self, transaction_id: str) -> Transaction:
        """Delete one transaction and return the deleted value."""
        validate_transaction_id(transaction_id)
        transactions = list(self._transactions.iter_all())
        transaction_index = next(
            (
                index
                for index, transaction in enumerate(transactions)
                if transaction.id == transaction_id
            ),
            None,
        )
        if transaction_index is None:
            raise ValueError(f"해당 ID의 거래가 없습니다: {transaction_id}")

        deleted = transactions.pop(transaction_index)
        self._transactions.replace_all(transactions)
        return deleted
