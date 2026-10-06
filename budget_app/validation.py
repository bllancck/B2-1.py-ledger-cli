"""사용자 입력과 데이터 모델의 필드값을 검사합니다."""

import re
from collections.abc import Iterable
from datetime import date as calendar_date
from uuid import UUID


ALLOWED_TRANSACTION_TYPES = frozenset({"income", "expense"})
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
MONTH_PATTERN = re.compile(r"\d{4}-\d{2}\Z")


def validate_transaction_id(value: str) -> None:
    """거래 ID가 올바른 UUID 문자열인지 검사합니다."""
    if not isinstance(value, str):
        raise ValueError("거래 ID는 UUID 형식의 문자열이어야 합니다.")

    try:
        UUID(value)
    except ValueError as error:
        raise ValueError("거래 ID는 유효한 UUID 문자열이어야 합니다.") from error


def validate_transaction_type(value: str) -> None:
    """거래 유형이 income 또는 expense인지 검사합니다."""
    if not isinstance(value, str) or value not in ALLOWED_TRANSACTION_TYPES:
        raise ValueError("거래 유형은 income 또는 expense여야 합니다.")


def validate_date(value: str) -> None:
    """날짜가 YYYY-MM-DD 형식이며 달력에 실제로 존재하는지 검사합니다."""
    if not isinstance(value, str) or DATE_PATTERN.fullmatch(value) is None:
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다. 예: 2024-01-15")

    try:
        calendar_date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("날짜는 실제 달력에 존재하는 날짜여야 합니다.") from error


def validate_month(value: str) -> None:
    """월이 YYYY-MM 형식이며 01월부터 12월 사이인지 검사합니다."""
    if not isinstance(value, str) or MONTH_PATTERN.fullmatch(value) is None:
        raise ValueError("월은 YYYY-MM 형식이어야 합니다. 예: 2024-01")

    month = int(value[5:])
    if month < 1 or month > 12:
        raise ValueError("월은 01부터 12 사이여야 합니다.")


def validate_amount(value: int) -> None:
    """금액이 bool이 아닌 0보다 큰 정수인지 검사합니다."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("금액은 0보다 큰 정수여야 합니다.")


def validate_limit(value: int) -> None:
    """조회할 거래 개수가 0보다 큰 정수인지 검사합니다."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("조회 건수는 0보다 큰 정수여야 합니다.")


def validate_top(value: int) -> None:
    """출력할 지출 카테고리 순위 개수가 0보다 큰 정수인지 검사합니다."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("상위 카테고리 수는 0보다 큰 정수여야 합니다.")


def validate_category_name(value: str) -> None:
    """카테고리 이름이 공백만 있는 값이 아닌 문자열인지 검사합니다."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("카테고리는 비어 있을 수 없습니다.")


def validate_registered_category(
    value: str,
    registered_categories: Iterable[str],
) -> None:
    """카테고리 이름이 등록된 카테고리 목록에 있는지 검사합니다."""
    validate_category_name(value)
    if value not in registered_categories:
        raise ValueError(
            "등록되지 않은 카테고리입니다. 카테고리를 먼저 등록하세요."
        )


def validate_memo(value: str) -> None:
    """선택 입력인 메모가 문자열인지 검사합니다."""
    if not isinstance(value, str):
        raise ValueError("메모는 문자열이어야 합니다.")


def validate_tags(value: list[str]) -> None:
    """태그가 비어 있지 않은 문자열들로 이루어진 목록인지 검사합니다."""
    if not isinstance(value, list):
        raise ValueError("태그는 문자열 목록이어야 합니다.")
    if any(not isinstance(tag, str) or not tag.strip() for tag in value):
        raise ValueError("각 태그는 비어 있지 않은 문자열이어야 합니다.")
