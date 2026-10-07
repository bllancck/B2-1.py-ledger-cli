"""CLI를 초기화하고 파싱된 명령을 해당 실행 함수로 전달합니다."""

from argparse import Namespace
from collections.abc import Callable, Sequence

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
from budget_app.decorators import handle_cli_errors
from budget_app.parser import build_parser
from budget_app.repository import initialize_data_files


CommandHandler = Callable[[Namespace], int]

COMMAND_HANDLERS: dict[str, CommandHandler] = {
    "add": run_add_command,
    "list": run_list_command,
    "search": run_search_command,
    "summary": run_summary_command,
    "budget": run_budget_command,
    "update": run_update_command,
    "delete": run_delete_command,
    "category": run_category_command,
    "import": run_import_command,
    "export": run_export_command,
}


@handle_cli_errors
def main(argv: Sequence[str] | None = None) -> int:
    """명령줄 인자를 해석해 해당 명령을 실행하고 종료 코드를 반환합니다."""
    parser = build_parser()
    args = parser.parse_args(argv)
    initialize_data_files(args.data_dir)

    handler = COMMAND_HANDLERS.get(args.command)
    if handler is not None:
        return handler(args)

    parser.print_help()
    return 0
