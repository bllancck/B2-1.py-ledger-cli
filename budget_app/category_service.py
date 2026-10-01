"""Apply business rules for category management."""

from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.validation import validate_category_name


class CategoryService:
    """Apply category management rules across repositories."""

    def __init__(
        self,
        category_repository: CategoryRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._categories = category_repository
        self._transactions = transaction_repository

    def add_category(self, name: str) -> str:
        """Add a new category and return its normalized name."""
        validate_category_name(name)
        category = name.strip()
        if category in self.list_categories():
            raise ValueError(f"이미 등록된 카테고리입니다: {category}")

        self._categories.append(category)
        return category

    def list_categories(self) -> list[str]:
        """Return categories in their stored order."""
        return list(self._categories.iter_all())

    def remove_category(self, name: str) -> str:
        """Remove an unused category and return its normalized name."""
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
