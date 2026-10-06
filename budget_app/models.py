"""애플리케이션에서 사용하는 데이터 구조를 정의합니다."""

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
    """검증을 마친 수입 또는 지출 거래 한 건을 나타냅니다."""

    id: str
    type: TransactionType
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """거래 객체가 만들어진 직후 모든 필드가 올바른지 검사합니다."""
        validate_transaction_id(self.id)
        validate_transaction_type(self.type)
        validate_date(self.date)
        validate_amount(self.amount)
        validate_category_name(self.category)
        validate_memo(self.memo)
        validate_tags(self.tags)
