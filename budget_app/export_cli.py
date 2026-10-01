"""Configure and handle the transaction CSV export command."""

import argparse
from pathlib import Path

from budget_app.decorators import handle_cli_errors
from budget_app.export_service import ExportService
from budget_app.repository import CategoryRepository, TransactionRepository
from budget_app.transaction_service import TransactionService


def configure_export_parser(parser: argparse.ArgumentParser) -> None:
    """Configure CSV output and period options."""
    parser.add_argument(
        "--out",
        required=True,
        dest="output_path",
        type=Path,
        metavar="CSV",
        help="생성할 UTF-8 CSV 파일",
    )
    parser.add_argument("--month", metavar="YYYY-MM")
    parser.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD")
    parser.set_defaults(handler=run_export_command)


@handle_cli_errors
def run_export_command(args: argparse.Namespace) -> int:
    """Export matching transactions and print the output count."""
    transaction_service = TransactionService(
        TransactionRepository(args.data_dir),
        CategoryRepository(args.data_dir),
    )
    exported = ExportService(transaction_service).export_csv(
        args.output_path,
        month=args.month,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    print(f"[완료] {args.output_path} ({exported} records)")
    return 0
