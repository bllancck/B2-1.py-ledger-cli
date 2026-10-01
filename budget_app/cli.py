"""Parse command-line input and display CLI output."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from budget_app.budget_cli import configure_budget_parser
from budget_app.category_cli import configure_category_parser
from budget_app.export_cli import configure_export_parser
from budget_app.import_cli import configure_import_parser
from budget_app.repository import initialize_data_files
from budget_app.summary_cli import configure_summary_parser
from budget_app.transaction_cli import configure_add_parser
from budget_app.transaction_mutation_cli import (
    configure_delete_parser,
    configure_update_parser,
)
from budget_app.transaction_query_cli import (
    configure_list_parser,
    configure_search_parser,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the application's top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="budget_app",
        description="파일 기반 용돈 기입장 CLI",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        metavar="PATH",
        help="데이터 저장 폴더 (기본값: ./data)",
    )
    commands = parser.add_subparsers(dest="command", title="commands")
    add_parser = commands.add_parser(
        "add",
        help="거래 추가",
        description="대화형 입력으로 수입 또는 지출 거래를 추가합니다.",
    )
    configure_add_parser(add_parser)
    list_parser = commands.add_parser(
        "list",
        help="최신 거래 목록 조회",
        description="최근에 추가된 거래부터 조회합니다.",
    )
    configure_list_parser(list_parser)
    search_parser = commands.add_parser(
        "search",
        help="조건으로 거래 검색",
        description="기간, 카테고리, 유형, 메모, 태그로 거래를 검색합니다.",
    )
    configure_search_parser(search_parser)
    summary_parser = commands.add_parser(
        "summary",
        help="월별 거래 요약",
        description="월별 수입, 지출, 잔액과 지출 카테고리 순위를 조회합니다.",
    )
    configure_summary_parser(summary_parser)
    budget_parser = commands.add_parser(
        "budget",
        help="월별 예산 관리",
        description="월별 지출 예산을 설정합니다.",
    )
    configure_budget_parser(budget_parser)
    update_parser = commands.add_parser(
        "update",
        help="ID로 거래 수정",
        description="지정한 거래의 선택한 필드를 수정합니다.",
    )
    configure_update_parser(update_parser)
    delete_parser = commands.add_parser(
        "delete",
        help="ID로 거래 삭제",
        description="지정한 거래를 삭제합니다.",
    )
    configure_delete_parser(delete_parser)
    category_parser = commands.add_parser(
        "category",
        help="카테고리 관리",
        description="거래에 사용할 카테고리를 관리합니다.",
    )
    configure_category_parser(category_parser)
    import_parser = commands.add_parser(
        "import",
        help="CSV 거래 가져오기",
        description="UTF-8 CSV 파일의 거래를 일괄 등록합니다.",
    )
    configure_import_parser(import_parser)
    export_parser = commands.add_parser(
        "export",
        help="CSV 거래 내보내기",
        description="월 또는 날짜 범위에 해당하는 거래를 UTF-8 CSV로 저장합니다.",
    )
    configure_export_parser(export_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    initialize_data_files(args.data_dir)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
