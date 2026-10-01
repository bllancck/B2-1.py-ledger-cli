"""Calculate monthly transaction summaries."""

from collections import defaultdict
from dataclasses import dataclass

from budget_app.repository import BudgetRepository, TransactionRepository
from budget_app.validation import validate_month, validate_top


@dataclass(frozen=True)
class MonthlySummary:
    """Contain calculated totals and ranked expense categories for one month."""

    month: str
    total_income: int
    total_expense: int
    top_expense_categories: list[tuple[str, int]]
    budget: int | None

    @property
    def balance(self) -> int:
        """Return income minus expense."""
        return self.total_income - self.total_expense

    @property
    def budget_usage_rate(self) -> float | None:
        """Return the percentage of the budget spent when a budget exists."""
        if self.budget is None:
            return None
        return self.total_expense / self.budget * 100

    @property
    def is_budget_exceeded(self) -> bool:
        """Return whether expenses are greater than the configured budget."""
        return self.budget is not None and self.total_expense > self.budget

    @property
    def budget_overage(self) -> int:
        """Return the amount over budget, or zero when within budget."""
        if self.budget is None:
            return 0
        return max(self.total_expense - self.budget, 0)


class SummaryService:
    """Aggregate transactions into a monthly summary."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        budget_repository: BudgetRepository | None = None,
    ) -> None:
        self._transactions = transaction_repository
        self._budgets = budget_repository

    def summarize_month(self, month: str, top: int) -> MonthlySummary | None:
        """Return a monthly summary, or None when the month has no transactions."""
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
