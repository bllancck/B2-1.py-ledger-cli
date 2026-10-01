"""Export filtered transactions to UTF-8 CSV files."""

import csv
from calendar import monthrange
from collections.abc import Iterator
from pathlib import Path

from budget_app.models import Transaction
from budget_app.transaction_service import TransactionService
from budget_app.validation import validate_date, validate_month


CSV_COLUMNS = ("date", "type", "category", "amount", "memo", "tags")


class ExportService:
    """Select transactions by period and write the shared CSV schema."""

    def __init__(self, transaction_service: TransactionService) -> None:
        self._transactions = transaction_service

    def export_csv(
        self,
        output_path: Path,
        *,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        """Export matching transactions and return the written row count."""
        transactions = self._select_transactions(
            month=month,
            date_from=date_from,
            date_to=date_to,
        )
        exported = 0

        try:
            with output_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                for transaction in transactions:
                    writer.writerow(self._to_csv_row(transaction))
                    exported += 1
        except OSError as error:
            raise ValueError(f"CSV 파일을 쓸 수 없습니다: {output_path}") from error

        return exported

    def _select_transactions(
        self,
        *,
        month: str | None,
        date_from: str | None,
        date_to: str | None,
    ) -> Iterator[Transaction]:
        """Validate period options and return the matching transaction stream."""
        if month is None and date_from is None and date_to is None:
            raise ValueError("--month 또는 --from/--to 기간 조건이 필요합니다.")
        if month is not None and (date_from is not None or date_to is not None):
            raise ValueError("--month와 --from/--to는 함께 사용할 수 없습니다.")

        if month is not None:
            validate_month(month)
            year = int(month[:4])
            month_number = int(month[5:])
            last_day = monthrange(year, month_number)[1]
            date_from = f"{month}-01"
            date_to = f"{month}-{last_day:02d}"
        else:
            if date_from is not None:
                validate_date(date_from)
            if date_to is not None:
                validate_date(date_to)
            if date_from is not None and date_to is not None and date_from > date_to:
                raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")

        return self._transactions.iter_search_transactions(
            date_from=date_from,
            date_to=date_to,
        )

    @staticmethod
    def _to_csv_row(transaction: Transaction) -> dict[str, str | int]:
        """Convert one transaction to the import-compatible CSV fields."""
        return {
            "date": transaction.date,
            "type": transaction.type,
            "category": transaction.category,
            "amount": transaction.amount,
            "memo": transaction.memo,
            "tags": ",".join(transaction.tags),
        }
