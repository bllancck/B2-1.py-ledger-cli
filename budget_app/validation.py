"""Validate user input and model field values."""

import re
from collections.abc import Iterable
from datetime import date as calendar_date
from uuid import UUID


ALLOWED_TRANSACTION_TYPES = frozenset({"income", "expense"})
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
MONTH_PATTERN = re.compile(r"\d{4}-\d{2}\Z")


def validate_transaction_id(value: str) -> None:
    """Ensure that a transaction ID is a UUID string."""
    if not isinstance(value, str):
        raise ValueError("거래 ID는 UUID 형식의 문자열이어야 합니다.")

    try:
        UUID(value)
    except ValueError as error:
        raise ValueError("거래 ID는 유효한 UUID 문자열이어야 합니다.") from error


def validate_transaction_type(value: str) -> None:
    """Ensure that a transaction type is income or expense."""
    if not isinstance(value, str) or value not in ALLOWED_TRANSACTION_TYPES:
        raise ValueError("거래 유형은 income 또는 expense여야 합니다.")


def validate_date(value: str) -> None:
    """Ensure that a value is a real date in YYYY-MM-DD format."""
    if not isinstance(value, str) or DATE_PATTERN.fullmatch(value) is None:
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다. 예: 2024-01-15")

    try:
        calendar_date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("날짜는 실제 달력에 존재하는 날짜여야 합니다.") from error


def validate_month(value: str) -> None:
    """Ensure that a value identifies a real month in YYYY-MM format."""
    if not isinstance(value, str) or MONTH_PATTERN.fullmatch(value) is None:
        raise ValueError("월은 YYYY-MM 형식이어야 합니다. 예: 2024-01")

    month = int(value[5:])
    if month < 1 or month > 12:
        raise ValueError("월은 01부터 12 사이여야 합니다.")


def validate_amount(value: int) -> None:
    """Ensure that an amount is a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("금액은 0보다 큰 정수여야 합니다.")


def validate_limit(value: int) -> None:
    """Ensure that a result limit is a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("조회 건수는 0보다 큰 정수여야 합니다.")


def validate_top(value: int) -> None:
    """Ensure that an expense ranking size is a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("상위 카테고리 수는 0보다 큰 정수여야 합니다.")


def validate_category_name(value: str) -> None:
    """Ensure that a category name is a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("카테고리는 비어 있을 수 없습니다.")


def validate_registered_category(
    value: str,
    registered_categories: Iterable[str],
) -> None:
    """Ensure that a category exists in the registered category collection."""
    validate_category_name(value)
    if value not in registered_categories:
        raise ValueError(
            "등록되지 않은 카테고리입니다. category add로 먼저 등록하세요."
        )


def validate_memo(value: str) -> None:
    """Ensure that an optional memo is represented as a string."""
    if not isinstance(value, str):
        raise ValueError("메모는 문자열이어야 합니다.")


def validate_tags(value: list[str]) -> None:
    """Ensure that tags are represented as non-empty strings in a list."""
    if not isinstance(value, list):
        raise ValueError("태그는 문자열 목록이어야 합니다.")
    if any(not isinstance(tag, str) or not tag.strip() for tag in value):
        raise ValueError("각 태그는 비어 있지 않은 문자열이어야 합니다.")
