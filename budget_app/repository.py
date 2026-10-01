"""Read and write the application's JSONL data files."""

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from budget_app.models import Transaction
from budget_app.validation import (
    validate_amount,
    validate_category_name,
    validate_month,
)


TRANSACTIONS_FILENAME = "transactions.jsonl"
CATEGORIES_FILENAME = "categories.jsonl"
BUDGETS_FILENAME = "budgets.jsonl"


class JsonlFile:
    """Store dictionary records in a UTF-8 JSONL file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        """Create the parent directory and file without replacing existing data."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, record: Mapping[str, Any]) -> None:
        """Append one JSON record to the file."""
        self.initialize()
        serialized = json.dumps(dict(record), ensure_ascii=False)
        with self.path.open("a", encoding="utf-8", newline="") as data_file:
            data_file.write(f"{serialized}\n")

    def iter_records(self) -> Iterator[dict[str, Any]]:
        """Yield dictionary records one line at a time."""
        self.initialize()
        with self.path.open("r", encoding="utf-8") as data_file:
            for line_number, line in enumerate(data_file, start=1):
                if not line.strip():
                    continue
                yield self._parse_record(line, f"{line_number}번째 줄")

    def iter_records_reverse(self) -> Iterator[dict[str, Any]]:
        """Yield records from the end of the file without loading it all."""
        self.initialize()
        with self.path.open("rb") as data_file:
            data_file.seek(0, 2)
            position = data_file.tell()
            buffer = b""
            reverse_index = 0

            while position > 0:
                read_size = min(8192, position)
                position -= read_size
                data_file.seek(position)
                buffer = data_file.read(read_size) + buffer
                lines = buffer.split(b"\n")
                buffer = lines[0]

                for raw_line in reversed(lines[1:]):
                    if not raw_line.strip():
                        continue
                    reverse_index += 1
                    line = raw_line.decode("utf-8")
                    yield self._parse_record(
                        line,
                        f"파일 끝에서 {reverse_index}번째 레코드",
                    )

            if buffer.strip():
                reverse_index += 1
                yield self._parse_record(
                    buffer.decode("utf-8"),
                    f"파일 끝에서 {reverse_index}번째 레코드",
                )

    def _parse_record(self, line: str, location: str) -> dict[str, Any]:
        """Parse and validate one JSONL record."""
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{self.path}의 {location}가 올바른 JSON이 아닙니다."
            ) from error

        if not isinstance(record, dict):
            raise ValueError(f"{self.path}의 {location}는 JSON 객체여야 합니다.")
        return record

    def replace(self, records: Iterable[Mapping[str, Any]]) -> None:
        """Replace the file contents with the given records."""
        self.initialize()
        with self.path.open("w", encoding="utf-8", newline="") as data_file:
            for record in records:
                serialized = json.dumps(dict(record), ensure_ascii=False)
                data_file.write(f"{serialized}\n")


class TransactionRepository:
    """Persist and load validated transactions."""

    def __init__(self, data_dir: Path) -> None:
        self._file = JsonlFile(data_dir / TRANSACTIONS_FILENAME)

    @property
    def path(self) -> Path:
        return self._file.path

    def initialize(self) -> None:
        self._file.initialize()

    def append(self, transaction: Transaction) -> None:
        self._file.append(asdict(transaction))

    def iter_all(self) -> Iterator[Transaction]:
        for record in self._file.iter_records():
            yield self._to_transaction(record)

    def iter_latest(self) -> Iterator[Transaction]:
        """Yield transactions from most recently appended to oldest."""
        for record in self._file.iter_records_reverse():
            yield self._to_transaction(record)

    def replace_all(self, transactions: Iterable[Transaction]) -> None:
        """Replace all stored transactions while preserving their order."""
        self._file.replace(asdict(transaction) for transaction in transactions)

    def _to_transaction(self, record: dict[str, Any]) -> Transaction:
        """Convert one JSON record into a validated transaction."""
        try:
            return Transaction(**record)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{self.path}에 올바르지 않은 거래 데이터가 있습니다."
            ) from error


class CategoryRepository:
    """Persist and load category names."""

    def __init__(self, data_dir: Path) -> None:
        self._file = JsonlFile(data_dir / CATEGORIES_FILENAME)

    @property
    def path(self) -> Path:
        return self._file.path

    def initialize(self) -> None:
        self._file.initialize()

    def append(self, category: str) -> None:
        validate_category_name(category)
        self._file.append({"name": category})

    def iter_all(self) -> Iterator[str]:
        for record in self._file.iter_records():
            category = record.get("name")
            try:
                validate_category_name(category)
            except ValueError as error:
                raise ValueError(
                    f"{self.path}에 올바르지 않은 카테고리 데이터가 있습니다."
                ) from error
            yield category

    def remove(self, category: str) -> bool:
        """Remove a category and return whether it existed."""
        categories = list(self.iter_all())
        remaining = [item for item in categories if item != category]
        if len(remaining) == len(categories):
            return False

        self._file.replace({"name": item} for item in remaining)
        return True


class BudgetRepository:
    """Persist and load monthly budget records."""

    def __init__(self, data_dir: Path) -> None:
        self._file = JsonlFile(data_dir / BUDGETS_FILENAME)

    @property
    def path(self) -> Path:
        return self._file.path

    def initialize(self) -> None:
        self._file.initialize()

    def append(self, month: str, amount: int) -> None:
        validate_month(month)
        validate_amount(amount)
        self._file.append({"month": month, "amount": amount})

    def set(self, month: str, amount: int) -> None:
        """Store one budget for a month, replacing its previous value."""
        validate_month(month)
        validate_amount(amount)
        budgets = dict(self.iter_all())
        budgets[month] = amount
        self._file.replace(
            {"month": stored_month, "amount": stored_amount}
            for stored_month, stored_amount in budgets.items()
        )

    def get(self, month: str) -> int | None:
        """Return the latest stored budget for a month, if present."""
        validate_month(month)
        amount = None
        for stored_month, stored_amount in self.iter_all():
            if stored_month == month:
                amount = stored_amount
        return amount

    def iter_all(self) -> Iterator[tuple[str, int]]:
        for record in self._file.iter_records():
            month = record.get("month")
            amount = record.get("amount")
            try:
                validate_month(month)
                validate_amount(amount)
            except ValueError as error:
                raise ValueError(
                    f"{self.path}에 올바르지 않은 예산 데이터가 있습니다."
                ) from error
            yield month, amount


def initialize_data_files(data_dir: Path) -> None:
    """Create all required data files while preserving existing contents."""
    TransactionRepository(data_dir).initialize()
    CategoryRepository(data_dir).initialize()
    BudgetRepository(data_dir).initialize()
