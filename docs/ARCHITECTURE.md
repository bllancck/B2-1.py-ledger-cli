# 애플리케이션 구조

## 전체 구조

```text
                         사용자
                           |
                           v
                  +----------------+
                  |  __main__.py   |
                  | 프로그램 시작점 |
                  +----------------+
                           |
                           v
                  +----------------+
                  |     cli.py     |
                  |  분기·입출력   |
                  +----------------+
                    |             |
                    v             v
          +------------------+  +-------------------------+
          |    parser.py     |  |       services.py       |
          | 명령·옵션 정의    |  | 모든 기능의 업무 규칙   |
          +------------------+  +-------------------------+
                                      |
                                      v
                            +-----------------+
                            |  repository.py  |
                            | 데이터 저장/조회 |
                            +-----------------+
                                      |
                                      v
        +---------------------------------------+
        |              JSONL Files              |
        |                                       |
        | transactions.jsonl                    |
        | categories.jsonl                      |
        | budgets.jsonl                         |
        +---------------------------------------+


       +---------------+       +----------------+
       |   models.py   |<------| validation.py  |
       | 데이터 구조    |       | 데이터 검증     |
       +---------------+       +----------------+

       +-----------------+
       |  decorators.py  |
       | CLI 공통 오류 처리|
       +-----------------+
                |
                v
              cli.py
```

## 1. `parser.py` — 명령과 옵션 정의

`parser.py`는 `argparse`를 사용해 최상위 명령, 하위 작업과 각 옵션을 등록합니다. `build_parser()`는 완성된 파서를 반환하며 명령 실행이나 데이터 파일 접근은 담당하지 않습니다.

## 2. `cli.py` — 명령 분기와 사용자 입출력

`cli.py`는 `parser.py`에서 만든 파서로 인자를 해석하고, 파싱된 `command` 값을 기준으로 실행 함수를 직접 호출합니다. 각 실행 함수는 사용자 입력을 서비스에 전달하고 처리 결과를 화면에 출력합니다.

```text
사용자 명령어
     ↓
parser.py의 build_parser()
     ↓
cli.py의 main() 명시적 분기
     ↓
cli.py의 run_*_command()
     ↓
services.py의 기능별 Service
```

`argparse.set_defaults(handler=...)`를 사용하지 않아 명령어가 어느 함수로 연결되는지 `main()`에서 바로 확인할 수 있습니다.

## 3. `services.py` — 비즈니스 로직

`services.py`는 거래, 카테고리, 예산, 요약, CSV 가져오기·내보내기의 처리 규칙을 한곳에 모읍니다. 각 기능은 별도의 Service 클래스로 구분합니다. 거래 추가는 다음 순서로 처리됩니다.

```text
cli.py의 run_add_command()
        |
        v
services.py의 TransactionService
        |
        | 카테고리 존재 여부 확인
        | Transaction 생성
        | UUID 생성
        v
repository.py
        |
        v
transactions.jsonl
```

## 4. `repository.py` — 데이터 저장 및 조회

```text
JsonlFile
 ├─ JSONL 파일 생성
 ├─ 레코드 추가
 ├─ 레코드 조회
 ├─ 역순 조회
 └─ 전체 데이터 교체

TransactionRepository
 └─ transactions.jsonl 관리

CategoryRepository
 └─ categories.jsonl 관리

BudgetRepository
 └─ budgets.jsonl 관리
```

`JsonlFile`은 JSONL 파일의 공통 입출력을 제공하고, 각 도메인 저장소는 자신이 담당하는 데이터의 변환과 검증을 처리합니다.

## 5. `models.py` — 데이터 구조 정의

```text
Transaction
 ├─ id
 ├─ type
 ├─ date
 ├─ amount
 ├─ category
 ├─ memo
 └─ tags
```

`Transaction` 모델은 거래 한 건의 필드와 생성 시 적용할 검증 규칙을 정의합니다.

## 6. Transaction 처리 흐름

```text
Transaction
     |
     +-- parser.py
     |      └─ 거래 명령과 옵션 정의
     |
     +-- cli.py
     |      ├─ 거래 추가 입력
     |      ├─ 거래 목록과 검색 출력
     |      └─ 거래 수정과 삭제 출력
     |
     +-- services.py의 TransactionService
            ├─ 거래 생성
            ├─ 최신 거래 조회
            ├─ 조건 검색
            ├─ 수정
            └─ 삭제
```

거래 명령과 옵션은 `parser.py`, 입력과 출력은 `cli.py`에서 확인할 수 있고, 공통 비즈니스 로직은 `services.py`의 `TransactionService`가 담당합니다.

## 7. `validation.py` — 입력값 검증

```text
거래 ID       → UUID 형식인지 확인
거래 유형     → income / expense인지 확인
날짜          → YYYY-MM-DD 형식 및 실제 존재하는 날짜 확인
월            → YYYY-MM 형식 확인
금액          → 0보다 큰 정수인지 확인
카테고리      → 빈 문자열인지 확인
등록 카테고리 → 실제 등록된 카테고리인지 확인
조회 개수     → 양수인지 확인
메모          → 문자열인지 확인
태그          → 올바른 문자열 리스트인지 확인
```

공통 검증 함수를 모델과 서비스에서 함께 사용해 CLI 입력, CSV 가져오기, 저장 데이터 복원에 같은 규칙을 적용합니다.

## 8. `decorators.py` — 공통 CLI 예외 처리

```text
@handle_cli_errors
        |
        v
   CLI 함수 실행
        |
   +----+----------------+
   |         |           |
ValueError OSError   EOFError
   |         |           |
   +---------+-----------+
             |
             v
       오류 메시지 출력
             |
             v
        종료 코드 1
```

`@handle_cli_errors`는 예상 가능한 입력 및 파일 오류를 공통 형식으로 출력하고 종료 코드 `1`을 반환합니다.
