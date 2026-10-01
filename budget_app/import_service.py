"""Import transaction rows from UTF-8 CSV files."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from budget_app.models import TransactionType
from budget_app.transaction_service import TransactionService


REQUIRED_COLUMNS = frozenset({"date", "type", "category", "amount"})


@dataclass(frozen=True)
class SkippedRow:
    """Describe one CSV row that could not be imported."""

    line_number: int
    reason: str


@dataclass(frozen=True)
class ImportResult:
    """Contain the imported count and skipped row details."""

    imported: int
    skipped_rows: tuple[SkippedRow, ...]

    @property
    def skipped(self) -> int:
        """Return the number of skipped CSV rows."""
        return len(self.skipped_rows)


class ImportService:
    """Read CSV rows and add valid transactions one at a time."""

    def __init__(self, transaction_service: TransactionService) -> None:
        self._transactions = transaction_service

    def import_csv(self, source_path: Path) -> ImportResult:
        """Import valid rows and report invalid rows without stopping the file."""
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
        """Ensure that the CSV includes all required column names."""
        if fieldnames is None:
            raise ValueError("CSV 헤더가 없습니다.")

        missing_columns = sorted(REQUIRED_COLUMNS.difference(fieldnames))
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"CSV 필수 헤더가 없습니다: {missing}")

    def _import_row(self, row: dict[str | None, str | None]) -> None:
        """Convert and persist one CSV row using transaction validation rules."""
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
