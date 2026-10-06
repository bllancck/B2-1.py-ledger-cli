"""CLI를 초기화하고 파싱된 명령을 해당 실행 함수로 전달합니다."""

from collections.abc import Sequence

from budget_app.commands import (
    run_add_command,
    run_budget_command,
    run_category_command,
    run_delete_command,
    run_export_command,
    run_import_command,
    run_list_command,
    run_search_command,
    run_summary_command,
    run_update_command,
)
from budget_app.parser import build_parser
from budget_app.repository import initialize_data_files


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
