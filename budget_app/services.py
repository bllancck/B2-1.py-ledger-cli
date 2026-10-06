"""거래, 카테고리, 예산과 요약 관련 업무 규칙을 처리합니다."""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import islice
from uuid import uuid4

from budget_app.models import Transaction, TransactionType
from budget_app.repository import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)
from budget_app.validation import (
    validate_amount,
    validate_category_name,
    validate_date,
    validate_limit,
    validate_month,
    validate_registered_category,
    validate_tags,
    validate_top,
    validate_transaction_id,
    validate_transaction_type,
)

@dataclass(frozen=True)
class MonthlySummary:
    """한 달의 수입, 지출, 카테고리 순위와 예산 결과를 담습니다."""

    month: str
    total_income: int
    total_expense: int
    top_expense_categories: list[tuple[str, int]]
    budget: int | None

    @property
    def balance(self) -> int:
        """총수입에서 총지출을 뺀 잔액을 반환합니다."""
        return self.total_income - self.total_expense

    @property
    def budget_usage_rate(self) -> float | None:
        """예산이 있으면 지출액이 예산의 몇 퍼센트인지 반환합니다."""
        if self.budget is None:
            return None
        return self.total_expense / self.budget * 100

    @property
    def is_budget_exceeded(self) -> bool:
        """총지출이 설정된 예산을 초과했는지 반환합니다."""
        return self.budget is not None and self.total_expense > self.budget

    @property
    def budget_overage(self) -> int:
        """예산 초과 금액을 반환하며 초과하지 않았으면 0을 반환합니다."""
        if self.budget is None:
            return 0
        return max(self.total_expense - self.budget, 0)


class TransactionService:
    """거래 추가, 조회, 검색, 수정, 삭제의 업무 규칙을 처리합니다."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        category_repository: CategoryRepository,
    ) -> None:
        """거래와 카테고리 저장소를 받아 거래 서비스를 준비합니다."""
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
        """입력값을 검사하고 새로운 거래를 만들어 파일에 저장합니다."""
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
        """최근에 저장한 거래부터 지정한 개수만큼 차례로 반환합니다."""
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
        """모든 검색 조건을 만족하는 거래를 최근 저장 순서로 반환합니다."""
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
        """ID로 거래를 찾고 전달된 필드만 변경해 전체 거래를 다시 저장합니다."""
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
        """ID가 일치하는 거래를 삭제하고 삭제된 거래를 반환합니다."""
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


class CategoryService:
    """카테고리 등록, 조회, 삭제에 필요한 업무 규칙을 처리합니다."""

    def __init__(
        self,
        category_repository: CategoryRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        """카테고리와 거래 저장소를 받아 카테고리 서비스를 준비합니다."""
        self._categories = category_repository
        self._transactions = transaction_repository

    def add_category(self, name: str) -> str:
        """이름의 양쪽 공백을 제거하고 중복이 아니면 저장합니다."""
        validate_category_name(name)
        category = name.strip()
        if category in self.list_categories():
            raise ValueError(f"이미 등록된 카테고리입니다: {category}")

        self._categories.append(category)
        return category

    def list_categories(self) -> list[str]:
        """저장된 카테고리를 등록된 순서대로 모두 반환합니다."""
        return list(self._categories.iter_all())

    def remove_category(self, name: str) -> str:
        """거래에서 사용하지 않는 카테고리만 삭제하고 이름을 반환합니다."""
        validate_category_name(name)
        category = name.strip()

        if category not in self.list_categories():
            raise ValueError(f"등록되지 않은 카테고리입니다: {category}")

        if any(
            transaction.category == category
            for transaction in self._transactions.iter_all()
        ):
            raise ValueError(
                f"거래에서 사용 중인 카테고리는 삭제할 수 없습니다: {category}"
            )

        self._categories.remove(category)
        return category


class BudgetService:
    """월별 예산을 설정하고 조회하는 업무 규칙을 처리합니다."""

    def __init__(self, budget_repository: BudgetRepository) -> None:
        """예산 저장소를 받아 예산 서비스를 준비합니다."""
        self._budgets = budget_repository

    def set_budget(self, month: str, amount: int) -> tuple[str, int]:
        """월과 금액을 검사하고 해당 월의 예산을 저장합니다."""
        validate_month(month)
        validate_amount(amount)
        self._budgets.set(month, amount)
        return month, amount

    def get_budget(self, month: str) -> int | None:
        """지정한 월의 예산을 반환하고 저장된 예산이 없으면 None을 반환합니다."""
        validate_month(month)
        return self._budgets.get(month)


class SummaryService:
    """거래를 월별로 합산하고 예산과 비교한 요약을 만듭니다."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        budget_repository: BudgetRepository | None = None,
    ) -> None:
        """거래 저장소와 선택적인 예산 저장소를 받아 요약 서비스를 준비합니다."""
        self._transactions = transaction_repository
        self._budgets = budget_repository

    def summarize_month(self, month: str, top: int) -> MonthlySummary | None:
        """한 달의 거래를 집계하고 거래가 없으면 None을 반환합니다."""
        validate_month(month)
        validate_top(top)

        total_income = 0
        total_expense = 0
        expense_by_category: dict[str, int] = defaultdict(int)
        found = False

        for transaction in self._transactions.iter_all():
            if transaction.date[:7] != month:
                continue

            found = True
            if transaction.type == "income":
                total_income += transaction.amount
            else:
                total_expense += transaction.amount
                expense_by_category[transaction.category] += transaction.amount

        if not found:
            return None

        ranked_expenses = sorted(
            expense_by_category.items(),
            key=lambda item: (-item[1], item[0]),
        )[:top]
        return MonthlySummary(
            month=month,
            total_income=total_income,
            total_expense=total_expense,
            top_expense_categories=ranked_expenses,
            budget=self._budgets.get(month) if self._budgets is not None else None,
        )
