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
                  | 명령어 진입점   |
                  +----------------+
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
   +-------------+  +-------------+  +-------------+
   | transaction |  |  category   |  |   budget    |
   |   *_cli.py  |  |   *_cli.py  |  |   *_cli.py |
   +-------------+  +-------------+  +-------------+
          |                |                |
          +----------------+----------------+
                           |
                           v
              +-------------------------+
              |      Service Layer      |
              |                         |
              | transaction_service.py  |
              | category_service.py     |
              | budget_service.py       |
              | summary_service.py      |
              | import_service.py       |
              | export_service.py       |
              +-------------------------+
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
            *_cli.py
```

## 1. `cli.py` — 전체 CLI 진입점

`cli.py`는 사용자 명령어를 해석하고 각 기능의 `*_cli.py`로 연결하는 라우터 역할을 합니다.

```text
사용자 명령어
     ↓
   cli.py
     ↓
각 기능의 *_cli.py
```

## 2. `*_cli.py` — 사용자 입력과 출력

CLI 모듈은 사용자 입력을 서비스에 전달하고 처리 결과를 화면에 출력합니다.

```text
CLI
 │
 │ 사용자 입력을 받음
 v
Service
 │
 │ 처리 결과 반환
 v
CLI
 │
 v
화면 출력
```

## 3. `*_service.py` — 비즈니스 로직

서비스 계층은 카테고리 확인, 모델 생성, 검색과 집계 같은 실제 처리 규칙을 담당합니다. 거래 추가는 다음 순서로 처리됩니다.

```text
transaction_cli.py
        |
        v
transaction_service.py
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

## 6. Transaction 관련 모듈 — 거래 기능 세분화

```text
Transaction
     |
     +-- transaction_cli.py
     |      └─ 거래 추가 입력
     |
     +-- transaction_query_cli.py
     |      ├─ 거래 목록
     |      └─ 거래 검색
     |
     +-- transaction_mutation_cli.py
     |      ├─ 거래 수정
     |      └─ 거래 삭제
     |
     +-- transaction_service.py
            ├─ 거래 생성
            ├─ 최신 거래 조회
            ├─ 조건 검색
            ├─ 수정
            └─ 삭제
```

거래 CLI는 추가, 조회, 변경 책임에 따라 세 모듈로 나뉘며 공통 비즈니스 로직은 `transaction_service.py`가 담당합니다.

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
