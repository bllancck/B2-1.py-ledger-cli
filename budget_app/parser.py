"""용돈 기입장 CLI가 지원하는 명령과 옵션을 정의합니다."""

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """지원하는 명령과 옵션을 등록한 최상위 인자 파서를 만듭니다."""
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
    commands.add_parser(
        "add",
        help="거래 추가",
        description="대화형 입력으로 수입 또는 지출 거래를 추가합니다.",
        epilog="사용할 카테고리는 category add로 먼저 등록하세요.",
    )
    list_parser = commands.add_parser(
        "list",
        help="최신 거래 목록 조회",
        description="최근에 추가된 거래부터 조회합니다.",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="출력할 최대 거래 수 (기본값: 10)",
    )
    search_parser = commands.add_parser(
        "search",
        help="조건으로 거래 검색",
        description="기간, 카테고리, 유형, 메모, 태그로 거래를 검색합니다.",
    )
    search_parser.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD")
    search_parser.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD")
    search_parser.add_argument("--category")
    search_parser.add_argument(
        "--type",
        dest="transaction_type",
        choices=("income", "expense"),
    )
    search_parser.add_argument("--q", dest="query", help="메모 검색어")
    search_parser.add_argument("--tag")
    summary_parser = commands.add_parser(
        "summary",
        help="월별 거래 요약",
        description="월별 수입, 지출, 잔액과 지출 카테고리 순위를 조회합니다.",
    )
    summary_parser.add_argument("--month", required=True, metavar="YYYY-MM")
    summary_parser.add_argument(
        "--top",
        type=int,
        default=3,
        metavar="N",
        help="출력할 지출 카테고리 수 (기본값: 3)",
    )
    budget_parser = commands.add_parser(
        "budget",
        help="월별 예산 관리",
        description="월별 지출 예산을 설정합니다.",
    )
    budget_actions = budget_parser.add_subparsers(
        dest="budget_action",
        title="actions",
        required=True,
    )
    budget_set_parser = budget_actions.add_parser("set", help="월별 예산 설정")
    budget_set_parser.add_argument("--month", required=True, metavar="YYYY-MM")
    budget_set_parser.add_argument(
        "--amount",
        required=True,
        type=int,
        metavar="AMOUNT",
    )
    update_parser = commands.add_parser(
        "update",
        help="ID로 거래 수정",
        description="지정한 거래의 선택한 필드를 수정합니다.",
        epilog="새 카테고리는 category add로 먼저 등록하세요.",
    )
    update_parser.add_argument("--id", required=True, dest="transaction_id")
    update_parser.add_argument("--date", metavar="YYYY-MM-DD")
    update_parser.add_argument(
        "--type",
        dest="transaction_type",
        choices=("income", "expense"),
    )
    update_parser.add_argument("--category")
    update_parser.add_argument("--amount", type=int)
    update_parser.add_argument("--memo")
    update_parser.add_argument("--tags", metavar="TAG1,TAG2")
    delete_parser = commands.add_parser(
        "delete",
        help="ID로 거래 삭제",
        description="지정한 거래를 삭제합니다.",
    )
    delete_parser.add_argument("--id", required=True, dest="transaction_id")
    category_parser = commands.add_parser(
        "category",
        help="카테고리 관리",
        description="거래에 사용할 카테고리를 관리합니다.",
    )
    category_actions = category_parser.add_subparsers(
        dest="category_action",
        title="actions",
        required=True,
    )
    category_actions.add_parser("add", help="카테고리 추가")
    category_actions.add_parser("list", help="카테고리 목록 조회")
    category_actions.add_parser("remove", help="카테고리 삭제")
    import_parser = commands.add_parser(
        "import",
        help="CSV 거래 가져오기",
        description="UTF-8 CSV 파일의 거래를 일괄 등록합니다.",
        epilog="CSV에 사용할 카테고리는 category add로 먼저 등록하세요.",
    )
    import_parser.add_argument(
        "--from",
        required=True,
        dest="source_path",
        type=Path,
        metavar="CSV",
        help="가져올 UTF-8 CSV 파일",
    )
    export_parser = commands.add_parser(
        "export",
        help="CSV 거래 내보내기",
        description="월 또는 날짜 범위에 해당하는 거래를 UTF-8 CSV로 저장합니다.",
        epilog=(
            "기간은 --month 또는 --from/--to 중 하나로 지정하세요. "
            "두 방식을 함께 사용할 수 없으며, --from이나 --to만 지정해도 됩니다."
        ),
    )
    export_parser.add_argument(
        "--out",
        required=True,
        dest="output_path",
        type=Path,
        metavar="CSV",
        help="생성할 UTF-8 CSV 파일",
    )
    export_parser.add_argument("--month", metavar="YYYY-MM")
    export_parser.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD")
    export_parser.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD")
    return parser
