"""Configure and handle category CLI commands."""

import argparse

from budget_app.category_service import CategoryService
from budget_app.decorators import handle_cli_errors
from budget_app.repository import CategoryRepository, TransactionRepository


def configure_category_parser(parser: argparse.ArgumentParser) -> None:
    """Add category actions to the category command parser."""
    actions = parser.add_subparsers(
        dest="category_action",
        title="actions",
        required=True,
    )

    add_parser = actions.add_parser("add", help="카테고리 추가")
    add_parser.set_defaults(handler=run_category_command)

    list_parser = actions.add_parser("list", help="카테고리 목록 조회")
    list_parser.set_defaults(handler=run_category_command)

    remove_parser = actions.add_parser("remove", help="카테고리 삭제")
    remove_parser.set_defaults(handler=run_category_command)


@handle_cli_errors
def run_category_command(args: argparse.Namespace) -> int:
    """Run the selected category action."""
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
