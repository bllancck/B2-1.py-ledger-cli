"""Configure and handle the transaction CSV import command."""

import argparse
from pathlib import Path

from budget_app.decorators import handle_cli_errors
from budget_app.import_service import ImportService
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.transaction_service import TransactionService


def configure_import_parser(parser: argparse.ArgumentParser) -> None:
    """Configure the CSV source option."""
    parser.add_argument(
        "--from",
        required=True,
        dest="source_path",
        type=Path,
        metavar="CSV",
        help="가져올 UTF-8 CSV 파일",
    )
    parser.set_defaults(handler=run_import_command)


@handle_cli_errors
def run_import_command(args: argparse.Namespace) -> int:
    """Import transactions and print row-level results."""
    transaction_service = TransactionService(
        TransactionRepository(args.data_dir),
        CategoryRepository(args.data_dir),
    )
    result = ImportService(transaction_service).import_csv(args.source_path)

    for skipped_row in result.skipped_rows:
        print(f"[건너뜀] {skipped_row.line_number}번째 줄: {skipped_row.reason}")
    print(f"[완료] imported={result.imported}, skipped={result.skipped}")
    return 0
