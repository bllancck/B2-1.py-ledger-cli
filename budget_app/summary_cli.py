"""Configure and handle the monthly summary CLI command."""

import argparse

from budget_app.decorators import handle_cli_errors
from budget_app.repository import BudgetRepository, TransactionRepository
from budget_app.summary_service import MonthlySummary, SummaryService


def configure_summary_parser(parser: argparse.ArgumentParser) -> None:
    """Configure monthly summary options."""
    parser.add_argument("--month", required=True, metavar="YYYY-MM")
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        metavar="N",
        help="출력할 지출 카테고리 수 (기본값: 3)",
    )
    parser.set_defaults(handler=run_summary_command)


def _print_summary(summary: MonthlySummary, top: int) -> None:
    """Print one calculated monthly summary."""
    print(f"총 수입: {summary.total_income}원")
    print(f"총 지출: {summary.total_expense}원")
    print(f"잔액: {summary.balance}원")
    if summary.budget is not None:
        usage_rate = summary.budget_usage_rate
        print(f"예산: {summary.budget}원 (사용률 {usage_rate:.1f}%)")
        if summary.is_budget_exceeded:
            print("예산 상태: 초과")
            print(f"[경고] 예산을 {summary.budget_overage}원 초과했습니다.")
        else:
            print("예산 상태: 이내")
    print()
    print(f"지출 TOP {top}")
    if not summary.top_expense_categories:
        print("지출 내역이 없습니다.")
        return

    for rank, (category, amount) in enumerate(
        summary.top_expense_categories,
        start=1,
    ):
        print(f"{rank}) {category} {amount}원")


@handle_cli_errors
def run_summary_command(args: argparse.Namespace) -> int:
    """Calculate and print a summary for the requested month."""
    service = SummaryService(
        TransactionRepository(args.data_dir),
        BudgetRepository(args.data_dir),
    )
    summary = service.summarize_month(args.month, args.top)

    if summary is None:
        print(f"데이터 없음: {args.month}")
        return 0

    _print_summary(summary, args.top)
    return 0
