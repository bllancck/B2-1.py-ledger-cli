"""Configure and handle monthly budget CLI commands."""

import argparse

from budget_app.budget_service import BudgetService
from budget_app.decorators import handle_cli_errors
from budget_app.repository import BudgetRepository


def configure_budget_parser(parser: argparse.ArgumentParser) -> None:
    """Add budget actions to the budget command parser."""
    actions = parser.add_subparsers(
        dest="budget_action",
        title="actions",
        required=True,
    )
    set_parser = actions.add_parser("set", help="월별 예산 설정")
    set_parser.add_argument("--month", required=True, metavar="YYYY-MM")
    set_parser.add_argument("--amount", required=True, type=int, metavar="AMOUNT")
    set_parser.set_defaults(handler=run_budget_command)


@handle_cli_errors
def run_budget_command(args: argparse.Namespace) -> int:
    """Set the requested monthly budget."""
    service = BudgetService(BudgetRepository(args.data_dir))
    month, amount = service.set_budget(args.month, args.amount)

    print(f"[저장 완료] {month} 예산 {amount}원")
    return 0
