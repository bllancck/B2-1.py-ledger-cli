"""Configure and handle read-only transaction CLI commands."""

import argparse
from typing import cast

from budget_app.decorators import handle_cli_errors
from budget_app.models import Transaction, TransactionType
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.transaction_service import TransactionService


def configure_list_parser(parser: argparse.ArgumentParser) -> None:
    """Configure the latest transaction list command."""
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="출력할 최대 거래 수 (기본값: 10)",
    )
    parser.set_defaults(handler=run_list_command)


def configure_search_parser(parser: argparse.ArgumentParser) -> None:
    """Configure transaction search filters."""
    parser.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD")
    parser.add_argument("--category")
    parser.add_argument(
        "--type",
        dest="transaction_type",
        choices=("income", "expense"),
    )
    parser.add_argument("--q", dest="query", help="메모 검색어")
    parser.add_argument("--tag")
    parser.set_defaults(handler=run_search_command)


def _format_transaction(transaction: Transaction) -> str:
    """Format one transaction for terminal output."""
    return (
        f"{transaction.id} | {transaction.date} | {transaction.type} | "
        f"{transaction.category} | {transaction.amount} | {transaction.memo}"
    )


def _build_service(args: argparse.Namespace) -> TransactionService:
    """Build a transaction service for a CLI data directory."""
    return TransactionService(
        TransactionRepository(args.data_dir),
        CategoryRepository(args.data_dir),
    )


@handle_cli_errors
def run_list_command(args: argparse.Namespace) -> int:
    """Print transactions from most recently added to oldest."""
    found = False
    for transaction in _build_service(args).iter_latest_transactions(args.limit):
        found = True
        print(_format_transaction(transaction))

    if not found:
        print("저장된 거래가 없습니다.")
    return 0


@handle_cli_errors
def run_search_command(args: argparse.Namespace) -> int:
    """Print transactions matching all supplied search filters."""
    transaction_type = cast(TransactionType | None, args.transaction_type)
    found = False
    transactions = _build_service(args).iter_search_transactions(
        date_from=args.date_from,
        date_to=args.date_to,
        category=args.category,
        transaction_type=transaction_type,
        query=args.query,
        tag=args.tag,
    )
    for transaction in transactions:
        found = True
        print(_format_transaction(transaction))

    if not found:
        print("검색 결과가 없습니다.")
    return 0
