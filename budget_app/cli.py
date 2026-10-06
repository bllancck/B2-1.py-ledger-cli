"""파싱된 명령을 실행하고 처리 결과를 화면에 출력합니다."""

from argparse import Namespace
from collections.abc import Callable, Sequence
from typing import cast

from budget_app.decorators import handle_cli_errors
from budget_app.models import Transaction, TransactionType
from budget_app.parser import build_parser
from budget_app.repository import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
    initialize_data_files,
)
from budget_app.services import (
    BudgetService,
    CategoryService,
    ExportService,
    ImportService,
    MonthlySummary,
    SummaryService,
    TransactionService,
)
from budget_app.validation import (
    validate_amount,
    validate_date,
    validate_registered_category,
    validate_tags,
    validate_transaction_type,
)


def _prompt_validated_text(
    prompt: str,
    validator: Callable[[str], None],
) -> str:
    """입력값이 검사를 통과할 때까지 안내 문구와 오류를 반복 출력합니다."""
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
    """사용자가 0보다 큰 정수 금액을 입력할 때까지 다시 입력받습니다."""
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
    """쉼표로 구분한 태그 문자열을 검사된 문자열 목록으로 바꿉니다."""
    if not raw_tags.strip():
        return []
    tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    validate_tags(tags)
    return tags


def _parse_optional_tags(raw_tags: str | None) -> list[str] | None:
    """수정용 태그 문자열이 있으면 목록으로 바꾸고 없으면 None을 반환합니다."""
    if raw_tags is None:
        return None
    return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]


def _format_transaction(transaction: Transaction) -> str:
    """거래 한 건을 터미널에 출력할 한 줄 문자열로 만듭니다."""
    return (
        f"{transaction.id} | {transaction.date} | {transaction.type} | "
        f"{transaction.category} | {transaction.amount} | {transaction.memo}"
    )


def _build_transaction_service(args: Namespace) -> TransactionService:
    """명령에서 받은 데이터 폴더를 사용하는 거래 서비스를 만듭니다."""
    return TransactionService(
        TransactionRepository(args.data_dir),
        CategoryRepository(args.data_dir),
    )


def _print_summary(summary: MonthlySummary, top: int) -> None:
    """계산된 월별 요약의 합계, 예산 상태와 지출 순위를 출력합니다."""
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
def run_add_command(args: Namespace) -> int:
    """거래 정보를 차례로 입력받아 새로운 거래 한 건을 저장합니다."""
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

    transaction = TransactionService(
        TransactionRepository(args.data_dir),
        categories,
    ).add_transaction(
        transaction_type=transaction_type,
        date=date,
        amount=amount,
        category=category,
        memo=memo,
        tags=tags,
    )

    print(f"[저장 완료] id={transaction.id}")
    return 0


@handle_cli_errors
def run_list_command(args: Namespace) -> int:
    """최근에 저장한 거래부터 요청한 개수만큼 출력합니다."""
    found = False
    service = _build_transaction_service(args)
    for transaction in service.iter_latest_transactions(args.limit):
        found = True
        print(_format_transaction(transaction))

    if not found:
        print("저장된 거래가 없습니다.")
    return 0


@handle_cli_errors
def run_search_command(args: Namespace) -> int:
    """사용자가 지정한 모든 검색 조건에 맞는 거래를 출력합니다."""
    transaction_type = cast(TransactionType | None, args.transaction_type)
    found = False
    transactions = _build_transaction_service(args).iter_search_transactions(
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


@handle_cli_errors
def run_update_command(args: Namespace) -> int:
    """ID로 거래를 찾고 사용자가 지정한 필드만 수정합니다."""
    transaction_type = cast(TransactionType | None, args.transaction_type)
    transaction = _build_transaction_service(args).update_transaction(
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
def run_delete_command(args: Namespace) -> int:
    """ID로 거래 한 건을 찾아 삭제합니다."""
    service = _build_transaction_service(args)
    transaction = service.delete_transaction(args.transaction_id)
    print(f"[삭제 완료] id={transaction.id}")
    return 0


@handle_cli_errors
def run_summary_command(args: Namespace) -> int:
    """지정한 월의 거래를 집계하고 월별 요약을 출력합니다."""
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


@handle_cli_errors
def run_budget_command(args: Namespace) -> int:
    """사용자가 지정한 월의 예산을 저장합니다."""
    service = BudgetService(BudgetRepository(args.data_dir))
    month, amount = service.set_budget(args.month, args.amount)
    print(f"[저장 완료] {month} 예산 {amount}원")
    return 0


@handle_cli_errors
def run_category_command(args: Namespace) -> int:
    """카테고리 추가, 목록 조회, 삭제 중 선택한 작업을 실행합니다."""
    service = CategoryService(
        CategoryRepository(args.data_dir),
        TransactionRepository(args.data_dir),
    )

    if args.category_action == "add":
        category = service.add_category(input("카테고리명: "))
        print(f"[저장 완료] category={category}")
    elif args.category_action == "list":
        categories = service.list_categories()
        if not categories:
            print("등록된 카테고리가 없습니다.")
        else:
            for category in categories:
                print(f"- {category}")
    elif args.category_action == "remove":
        category = service.remove_category(input("삭제할 카테고리명: "))
        print(f"[삭제 완료] category={category}")

    return 0


@handle_cli_errors
def run_import_command(args: Namespace) -> int:
    """CSV 거래를 가져오고 저장하거나 건너뛴 행의 결과를 출력합니다."""
    service = ImportService(_build_transaction_service(args))
    result = service.import_csv(args.source_path)

    for skipped_row in result.skipped_rows:
        print(f"[건너뜀] {skipped_row.line_number}번째 줄: {skipped_row.reason}")
    print(f"[완료] imported={result.imported}, skipped={result.skipped}")
    return 0


@handle_cli_errors
def run_export_command(args: Namespace) -> int:
    """기간에 맞는 거래를 CSV로 내보내고 저장한 건수를 출력합니다."""
    exported = ExportService(_build_transaction_service(args)).export_csv(
        args.output_path,
        month=args.month,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    print(f"[완료] {args.output_path} ({exported} records)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """명령줄 인자를 해석해 해당 명령을 실행하고 종료 코드를 반환합니다."""
    parser = build_parser()
    args = parser.parse_args(argv)
    initialize_data_files(args.data_dir)

    if args.command == "add":
        return run_add_command(args)
    if args.command == "list":
        return run_list_command(args)
    if args.command == "search":
        return run_search_command(args)
    if args.command == "summary":
        return run_summary_command(args)
    if args.command == "budget":
        return run_budget_command(args)
    if args.command == "update":
        return run_update_command(args)
    if args.command == "delete":
        return run_delete_command(args)
    if args.command == "category":
        return run_category_command(args)
    if args.command == "import":
        return run_import_command(args)
    if args.command == "export":
        return run_export_command(args)

    parser.print_help()
    return 0
