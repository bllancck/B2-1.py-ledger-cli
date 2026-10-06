"""여러 CLI 명령에서 함께 사용하는 데코레이터를 제공합니다."""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec


P = ParamSpec("P")


def handle_cli_errors(function: Callable[P, int]) -> Callable[P, int]:
    """예상 가능한 명령 오류와 해결 힌트를 출력하고 종료 코드 1을 반환합니다."""

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        """원래 함수를 실행하고 예상 가능한 예외를 공통 형식으로 처리합니다."""
        try:
            return function(*args, **kwargs)
        except ValueError as error:
            print(f"[오류] {error}")
            print("[힌트] 입력값과 데이터 파일을 확인한 뒤 다시 시도하세요.")
        except OSError as error:
            print(f"[오류] 파일을 처리할 수 없습니다: {error}")
            print("[힌트] 데이터 경로와 파일 권한을 확인하세요.")
        except EOFError:
            print("[오류] 입력이 완료되기 전에 종료되었습니다.")
            print("[힌트] 필요한 값을 다시 입력해 명령을 실행하세요.")
        return 1

    return wrapper
