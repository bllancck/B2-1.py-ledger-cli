"""Apply business rules for monthly budgets."""

from budget_app.repository import BudgetRepository
from budget_app.validation import validate_amount, validate_month


class BudgetService:
    """Set and retrieve one budget amount per month."""

    def __init__(self, budget_repository: BudgetRepository) -> None:
        self._budgets = budget_repository

    def set_budget(self, month: str, amount: int) -> tuple[str, int]:
        """Validate and persist a monthly budget."""
        validate_month(month)
        validate_amount(amount)
        self._budgets.set(month, amount)
        return month, amount

    def get_budget(self, month: str) -> int | None:
        """Return the budget for a month when one is stored."""
        validate_month(month)
        return self._budgets.get(month)
