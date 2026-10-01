"""Define application data models."""

from dataclasses import dataclass, field
from typing import Literal

from budget_app.validation import (
    validate_amount,
    validate_category_name,
    validate_date,
    validate_memo,
    validate_tags,
    validate_transaction_id,
    validate_transaction_type,
)


TransactionType = Literal["income", "expense"]


@dataclass
class Transaction:
    """Represent one validated income or expense transaction."""

    id: str
    type: TransactionType
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate field values immediately after initialization."""
        validate_transaction_id(self.id)
        validate_transaction_type(self.type)
        validate_date(self.date)
        validate_amount(self.amount)
        validate_category_name(self.category)
        validate_memo(self.memo)
        validate_tags(self.tags)
