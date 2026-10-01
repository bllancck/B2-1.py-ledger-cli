"""Provide decorators for shared CLI concerns."""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec


P = ParamSpec("P")


def handle_cli_errors(function: Callable[P, int]) -> Callable[P, int]:
    """Print expected CLI errors with a hint and return a nonzero exit code."""

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
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
