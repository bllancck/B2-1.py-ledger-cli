"""Configure and handle transaction update and delete commands."""

import argparse
from typing import cast

from budget_app.decorators import handle_cli_errors
from budget_app.models import TransactionType
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.transaction_service import TransactionService


def configure_update_parser(parser: argparse.ArgumentParser) -> None:
    """Configure option-based transaction updates."""
    parser.add_argument("--id", required=True, dest="transaction_id")
    parser.add_argument("--date", metavar="YYYY-MM-DD")
    parser.add_argument(
        "--type",
        dest="transaction_type",
        choices=("income", "expense"),
    )
    parser.add_argument("--category")
    parser.add_argument("--amount", type=int)
    parser.add_argument("--memo")
    parser.add_argument("--tags", metavar="TAG1,TAG2")
    parser.set_defaults(handler=run_update_command)


def configure_delete_parser(parser: argparse.ArgumentParser) -> None:
    """Configure transaction deletion by ID."""
    parser.add_argument("--id", required=True, dest="transaction_id")
    parser.set_defaults(handler=run_delete_command)


def _build_service(args: argparse.Namespace) -> TransactionService:
    """Build a transaction service for a CLI data directory."""
    return TransactionService(
        TransactionRepository(args.data_dir),
        CategoryRepository(args.data_dir),
    )


def _parse_optional_tags(raw_tags: str | None) -> list[str] | None:
    """Parse an optional comma-separated tag update."""
    if raw_tags is None:
        return None
    return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]


@handle_cli_errors
def run_update_command(args: argparse.Namespace) -> int:
    """Update selected fields of a transaction."""
    transaction_type = cast(TransactionType | None, args.transaction_type)
    transaction = _build_service(args).update_transaction(
        args.transaction_id,
        date=args.date,
        transaction_type=transaction_type,
        category=args.category,
        amount=args.amount,
        memo=args.memo,
        tags=_parse_optional_tags(args.tags),
    )

    print(f"[수정 완료] id={transaction.id}")
    return 0


@handle_cli_errors
def run_delete_command(args: argparse.Namespace) -> int:
    """Delete one transaction by ID."""
    transaction = _build_service(args).delete_transaction(args.transaction_id)

    print(f"[삭제 완료] id={transaction.id}")
    return 0
