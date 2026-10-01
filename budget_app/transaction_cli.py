"""Configure and handle transaction CLI commands."""

import argparse
from collections.abc import Callable
from typing import cast

from budget_app.decorators import handle_cli_errors
from budget_app.models import TransactionType
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.transaction_service import TransactionService
from budget_app.validation import (
    validate_amount,
    validate_date,
    validate_registered_category,
    validate_tags,
    validate_transaction_type,
)


def configure_add_parser(parser: argparse.ArgumentParser) -> None:
    """Configure the interactive transaction add command."""
    parser.set_defaults(handler=run_add_command)


def _prompt_validated_text(
    prompt: str,
    validator: Callable[[str], None],
) -> str:
    """Prompt until a text value passes validation."""
    while True:
        value = input(prompt).strip()
        try:
            validator(value)
        except ValueError as error:
            print(f"[오류] {error}")
            print("[힌트] 올바른 형식으로 다시 입력하세요.")
            continue
        return value


def _prompt_amount() -> int:
    """Prompt until a positive integer amount is entered."""
    while True:
        raw_amount = input("금액(양수 정수): ").strip()
        try:
            amount = int(raw_amount)
            validate_amount(amount)
        except ValueError:
            print("[오류] 금액은 0보다 큰 정수여야 합니다.")
            print("[힌트] 1 이상의 정수를 입력하세요.")
            continue
        return amount


def _parse_tags(raw_tags: str) -> list[str]:
    """Convert comma-separated tag input into a validated list."""
    if not raw_tags.strip():
        return []
    tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    validate_tags(tags)
    return tags


@handle_cli_errors
def run_add_command(args: argparse.Namespace) -> int:
    """Interactively collect and persist one transaction."""
    categories = CategoryRepository(args.data_dir)
    registered_categories = list(categories.iter_all())
    if not registered_categories:
        print("[오류] 등록된 카테고리가 없습니다.")
        print("[힌트] category add로 카테고리를 먼저 등록하세요.")
        return 1

    date = _prompt_validated_text("날짜(YYYY-MM-DD): ", validate_date)
    transaction_type = cast(
        TransactionType,
        _prompt_validated_text(
            "타입(income/expense): ",
            validate_transaction_type,
        ),
    )
    category = _prompt_validated_text(
        "카테고리: ",
        lambda value: validate_registered_category(value, registered_categories),
    )
    amount = _prompt_amount()
    memo = input("메모(선택): ")
    tags = _parse_tags(input("태그(쉼표로 구분, 없으면 엔터): "))

    service = TransactionService(
        TransactionRepository(args.data_dir),
        categories,
    )
    transaction = service.add_transaction(
        transaction_type=transaction_type,
        date=date,
        amount=amount,
        category=category,
        memo=memo,
        tags=tags,
    )

    print(f"[저장 완료] id={transaction.id}")
    return 0
