"""거래 CSV 가져오기와 내보내기에 필요한 업무 규칙을 처리합니다."""

import csv
from calendar import monthrange
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from budget_app.models import Transaction, TransactionType
from budget_app.services import TransactionService
from budget_app.validation import validate_date, validate_month


REQUIRED_COLUMNS = frozenset({"date", "type", "category", "amount"})
CSV_COLUMNS = ("date", "type", "category", "amount", "memo", "tags")


@dataclass(frozen=True)
class SkippedRow:
    """CSV 가져오기에서 저장하지 못한 행의 위치와 이유를 나타냅니다."""

    line_number: int
    reason: str


@dataclass(frozen=True)
class ImportResult:
    """CSV 가져오기로 저장한 행 수와 건너뛴 행들을 담습니다."""

    imported: int
    skipped_rows: tuple[SkippedRow, ...]

    @property
    def skipped(self) -> int:
        """가져오지 못하고 건너뛴 CSV 행의 개수를 반환합니다."""
        return len(self.skipped_rows)


class ImportService:
    """UTF-8 CSV 파일의 거래를 읽어 유효한 행을 저장합니다."""

    def __init__(self, transaction_service: TransactionService) -> None:
        """거래를 저장할 거래 서비스를 받아 가져오기 서비스를 준비합니다."""
        self._transactions = transaction_service

    def import_csv(self, source_path: Path) -> ImportResult:
        """CSV의 정상 행은 저장하고 잘못된 행은 이유와 함께 결과에 담습니다."""
        imported = 0
        skipped_rows: list[SkippedRow] = []

        try:
            with source_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                self._validate_headers(reader.fieldnames)

                for row in reader:
                    try:
                        self._import_row(row)
                    except ValueError as error:
                        skipped_rows.append(SkippedRow(reader.line_num, str(error)))
                    else:
                        imported += 1
        except FileNotFoundError as error:
            raise ValueError(f"CSV 파일을 찾을 수 없습니다: {source_path}") from error
        except UnicodeDecodeError as error:
            raise ValueError("CSV 파일은 UTF-8 인코딩이어야 합니다.") from error
        except csv.Error as error:
            raise ValueError(f"CSV 형식을 읽을 수 없습니다: {error}") from error
        except OSError as error:
            raise ValueError(f"CSV 파일을 읽을 수 없습니다: {source_path}") from error

        return ImportResult(imported, tuple(skipped_rows))

    @staticmethod
    def _validate_headers(fieldnames: list[str] | None) -> None:
        """CSV 헤더에 거래 저장에 필요한 필수 열이 모두 있는지 검사합니다."""
        if fieldnames is None:
            raise ValueError("CSV 헤더가 없습니다.")

        missing_columns = sorted(REQUIRED_COLUMNS.difference(fieldnames))
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"CSV 필수 헤더가 없습니다: {missing}")

    def _import_row(self, row: dict[str | None, str | None]) -> None:
        """CSV 한 행을 거래 입력값으로 변환하고 거래 서비스를 통해 저장합니다."""
        if None in row:
            raise ValueError("헤더보다 값이 많은 행입니다.")

        raw_amount = (row.get("amount") or "").strip()
        try:
            amount = int(raw_amount)
        except ValueError as error:
            raise ValueError("금액은 0보다 큰 정수여야 합니다.") from error

        raw_tags = row.get("tags") or ""
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
        self._transactions.add_transaction(
            transaction_type=cast(
                TransactionType,
                (row.get("type") or "").strip(),
            ),
            date=(row.get("date") or "").strip(),
            amount=amount,
            category=(row.get("category") or "").strip(),
            memo=row.get("memo") or "",
            tags=tags,
        )


class ExportService:
    """기간에 맞는 거래를 선택해 UTF-8 CSV 파일로 저장합니다."""

    def __init__(self, transaction_service: TransactionService) -> None:
        """내보낼 거래를 조회할 거래 서비스를 받아 준비합니다."""
        self._transactions = transaction_service

    def export_csv(
        self,
        output_path: Path,
        *,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        """기간에 해당하는 거래를 CSV로 쓰고 저장한 행의 개수를 반환합니다."""
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
        """기간 조건을 검사하고 조건에 맞는 거래 반복자를 반환합니다."""
        if month is None and date_from is None and date_to is None:
            raise ValueError("월 또는 날짜 범위에 대한 기간 조건이 필요합니다.")
        if month is not None and (date_from is not None or date_to is not None):
            raise ValueError("월 조건과 날짜 범위는 함께 지정할 수 없습니다.")

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
        """거래 객체를 가져오기와 같은 형식의 CSV 한 행으로 변환합니다."""
        return {
            "date": transaction.date,
            "type": transaction.type,
            "category": transaction.category,
            "amount": transaction.amount,
            "memo": transaction.memo,
            "tags": ",".join(transaction.tags),
        }
