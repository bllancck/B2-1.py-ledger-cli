"""애플리케이션의 JSONL 데이터 파일을 읽고 씁니다."""

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
    """딕셔너리 레코드를 UTF-8 JSONL 파일에 저장합니다."""

    def __init__(self, path: Path) -> None:
        """데이터를 읽고 쓸 JSONL 파일 경로를 저장합니다."""
        self.path = path

    def initialize(self) -> None:
        """기존 내용은 유지하면서 상위 폴더와 파일이 없으면 만듭니다."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, record: Mapping[str, Any]) -> None:
        """딕셔너리 한 건을 JSON 문자열로 바꿔 파일 끝에 추가합니다."""
        self.initialize()
        serialized = json.dumps(dict(record), ensure_ascii=False)
        with self.path.open("a", encoding="utf-8", newline="") as data_file:
            data_file.write(f"{serialized}\n")

    def iter_records(self) -> Iterator[dict[str, Any]]:
        """파일 앞에서부터 한 줄씩 읽어 딕셔너리로 반환합니다."""
        self.initialize()
        with self.path.open("r", encoding="utf-8") as data_file:
            for line_number, line in enumerate(data_file, start=1):
                if not line.strip():
                    continue
                yield self._parse_record(line, f"{line_number}번째 줄")

    def iter_records_reverse(self) -> Iterator[dict[str, Any]]:
        """전체 파일을 메모리에 올리지 않고 끝에서부터 레코드를 반환합니다."""
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
        """JSONL의 한 줄을 딕셔너리로 변환하고 올바른 형태인지 검사합니다."""
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
        """파일의 기존 내용을 지우고 전달받은 레코드들로 다시 씁니다."""
        self.initialize()
        with self.path.open("w", encoding="utf-8", newline="") as data_file:
            for record in records:
                serialized = json.dumps(dict(record), ensure_ascii=False)
                data_file.write(f"{serialized}\n")


class TransactionRepository:
    """검증된 거래를 JSONL 파일에 저장하고 불러옵니다."""

    def __init__(self, data_dir: Path) -> None:
        """데이터 폴더 안의 거래 파일을 사용하도록 준비합니다."""
        self._file = JsonlFile(data_dir / TRANSACTIONS_FILENAME)

    @property
    def path(self) -> Path:
        """현재 사용하는 거래 파일 경로를 반환합니다."""
        return self._file.path

    def initialize(self) -> None:
        """거래 파일과 상위 폴더가 없으면 만듭니다."""
        self._file.initialize()

    def append(self, transaction: Transaction) -> None:
        """거래 객체 한 건을 딕셔너리로 바꿔 파일 끝에 추가합니다."""
        self._file.append(asdict(transaction))

    def iter_all(self) -> Iterator[Transaction]:
        """저장된 모든 거래를 처음 저장한 순서대로 반환합니다."""
        for record in self._file.iter_records():
            yield self._to_transaction(record)

    def iter_latest(self) -> Iterator[Transaction]:
        """가장 최근에 저장한 거래부터 역순으로 반환합니다."""
        for record in self._file.iter_records_reverse():
            yield self._to_transaction(record)

    def replace_all(self, transactions: Iterable[Transaction]) -> None:
        """전달받은 거래 순서를 유지하면서 거래 파일 전체를 다시 씁니다."""
        self._file.replace(asdict(transaction) for transaction in transactions)

    def _to_transaction(self, record: dict[str, Any]) -> Transaction:
        """JSON 딕셔너리 한 건을 검증된 거래 객체로 변환합니다."""
        try:
            return Transaction(**record)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{self.path}에 올바르지 않은 거래 데이터가 있습니다."
            ) from error


class CategoryRepository:
    """카테고리 이름을 JSONL 파일에 저장하고 불러옵니다."""

    def __init__(self, data_dir: Path) -> None:
        """데이터 폴더 안의 카테고리 파일을 사용하도록 준비합니다."""
        self._file = JsonlFile(data_dir / CATEGORIES_FILENAME)

    @property
    def path(self) -> Path:
        """현재 사용하는 카테고리 파일 경로를 반환합니다."""
        return self._file.path

    def initialize(self) -> None:
        """카테고리 파일과 상위 폴더가 없으면 만듭니다."""
        self._file.initialize()

    def append(self, category: str) -> None:
        """카테고리 이름을 검사한 뒤 파일 끝에 추가합니다."""
        validate_category_name(category)
        self._file.append({"name": category})

    def iter_all(self) -> Iterator[str]:
        """저장된 카테고리를 등록된 순서대로 검사하며 반환합니다."""
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
        """카테고리를 삭제하고 실제로 존재했던 이름인지 반환합니다."""
        categories = list(self.iter_all())
        remaining = [item for item in categories if item != category]
        if len(remaining) == len(categories):
            return False

        self._file.replace({"name": item} for item in remaining)
        return True


class BudgetRepository:
    """월별 예산을 JSONL 파일에 저장하고 불러옵니다."""

    def __init__(self, data_dir: Path) -> None:
        """데이터 폴더 안의 예산 파일을 사용하도록 준비합니다."""
        self._file = JsonlFile(data_dir / BUDGETS_FILENAME)

    @property
    def path(self) -> Path:
        """현재 사용하는 예산 파일 경로를 반환합니다."""
        return self._file.path

    def initialize(self) -> None:
        """예산 파일과 상위 폴더가 없으면 만듭니다."""
        self._file.initialize()

    def append(self, month: str, amount: int) -> None:
        """월과 금액을 검사한 뒤 예산 한 건을 파일 끝에 추가합니다."""
        validate_month(month)
        validate_amount(amount)
        self._file.append({"month": month, "amount": amount})

    def set(self, month: str, amount: int) -> None:
        """해당 월의 기존 예산이 있으면 새 금액으로 바꿔 저장합니다."""
        validate_month(month)
        validate_amount(amount)
        budgets = dict(self.iter_all())
        budgets[month] = amount
        self._file.replace(
            {"month": stored_month, "amount": stored_amount}
            for stored_month, stored_amount in budgets.items()
        )

    def get(self, month: str) -> int | None:
        """지정한 월의 예산을 반환하고 저장된 값이 없으면 None을 반환합니다."""
        validate_month(month)
        amount = None
        for stored_month, stored_amount in self.iter_all():
            if stored_month == month:
                amount = stored_amount
        return amount

    def iter_all(self) -> Iterator[tuple[str, int]]:
        """저장된 모든 월별 예산을 검사하며 차례로 반환합니다."""
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
    """기존 내용은 유지하면서 거래, 카테고리, 예산 파일을 준비합니다."""
    TransactionRepository(data_dir).initialize()
    CategoryRepository(data_dir).initialize()
    BudgetRepository(data_dir).initialize()
