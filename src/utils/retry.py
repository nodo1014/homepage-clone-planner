"""
비동기 재시도 메커니즘

이 모듈은 비동기 함수에 대한 재시도 로직을 제공합니다.
일시적인 오류가 발생했을 때 지정된 횟수만큼 자동으로 재시도합니다.
"""
import asyncio
import logging
import time
from typing import Callable, Any, TypeVar, Optional, List, Dict, Union
from functools import wraps

# 로거 설정
logger = logging.getLogger(__name__)

# 타입 변수 정의
T = TypeVar('T')  # 함수 반환 타입
R = TypeVar('R')  # 재시도 조건 검사 함수의 인자 타입

# 재시도 가능한 예외 기본값
DEFAULT_RETRY_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


async def async_retry(
    func: Callable[..., Any],
    *args: Any,
    retry_count: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple = DEFAULT_RETRY_EXCEPTIONS,
    retry_on_result: Optional[Callable[[R], bool]] = None,
    **kwargs: Any
) -> Any:
    """
    비동기 함수를 실행하고 필요한 경우 재시도합니다.

    Args:
        func: 실행할 비동기 함수
        *args: 함수에 전달할 위치 인자
        retry_count: 최대 재시도 횟수 (기본값: 3)
        base_delay: 초기 지연 시간(초) (기본값: 1.0)
        max_delay: 최대 지연 시간(초) (기본값: 10.0)
        backoff_factor: 지수 백오프 계수 (기본값: 2.0)
        retry_exceptions: 재시도할 예외 유형 튜플 (기본값: CONNECTION_ERRORS)
        retry_on_result: 결과를 검사하여 재시도 여부를 결정하는 콜백 함수
        **kwargs: 함수에 전달할 키워드 인자

    Returns:
        함수의 반환값

    Raises:
        마지막 예외: 모든 재시도가 실패한 경우
    """
    last_exception = None
    attempt = 0

    while attempt <= retry_count:
        try:
            attempt += 1
            result = await func(*args, **kwargs)

            # 결과를 검사하여 재시도 여부 결정
            if retry_on_result and retry_on_result(result):
                if attempt <= retry_count:
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    logger.warning(
                        f"재시도 조건 충족 (결과: {result}). {attempt}/{retry_count} 번째 시도. "
                        f"{delay:.2f}초 후 재시도합니다."
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.warning(f"최대 재시도 횟수({retry_count})에 도달했습니다. 마지막 결과: {result}")
            
            return result

        except retry_exceptions as e:
            last_exception = e
            if attempt <= retry_count:
                delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                logger.warning(
                    f"오류 발생: {str(e)}. {attempt}/{retry_count} 번째 시도. "
                    f"{delay:.2f}초 후 재시도합니다."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"최대 재시도 횟수({retry_count})에 도달했습니다. 마지막 오류: {str(e)}")
                raise last_exception


def async_retry_decorator(
    retry_count: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple = DEFAULT_RETRY_EXCEPTIONS,
    retry_on_result: Optional[Callable[[R], bool]] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    비동기 함수에 재시도 로직을 추가하는 데코레이터

    Args:
        retry_count: 최대 재시도 횟수 (기본값: 3)
        base_delay: 초기 지연 시간(초) (기본값: 1.0)
        max_delay: 최대 지연 시간(초) (기본값: 10.0)
        backoff_factor: 지수 백오프 계수 (기본값: 2.0)
        retry_exceptions: 재시도할 예외 유형 튜플 (기본값: CONNECTION_ERRORS)
        retry_on_result: 결과를 검사하여 재시도 여부를 결정하는 콜백 함수

    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await async_retry(
                func,
                *args,
                retry_count=retry_count,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                retry_exceptions=retry_exceptions,
                retry_on_result=retry_on_result,
                **kwargs
            )
        return wrapper
    return decorator


class RetryConfig:
    """재시도 설정을 관리하는 클래스"""
    
    def __init__(
        self,
        retry_count: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0,
        retry_exceptions: tuple = DEFAULT_RETRY_EXCEPTIONS,
        retry_on_result: Optional[Callable[[Any], bool]] = None
    ):
        """
        재시도 설정 초기화

        Args:
            retry_count: 최대 재시도 횟수 (기본값: 3)
            base_delay: 초기 지연 시간(초) (기본값: 1.0)
            max_delay: 최대 지연 시간(초) (기본값: 10.0)
            backoff_factor: 지수 백오프 계수 (기본값: 2.0)
            retry_exceptions: 재시도할 예외 유형 튜플 (기본값: CONNECTION_ERRORS)
            retry_on_result: 결과를 검사하여 재시도 여부를 결정하는 콜백 함수
        """
        self.retry_count = retry_count
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retry_exceptions = retry_exceptions
        self.retry_on_result = retry_on_result
    
    async def retry(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        설정된 재시도 정책으로 함수를 실행합니다.

        Args:
            func: 실행할 비동기 함수
            *args: 함수에 전달할 위치 인자
            **kwargs: 함수에 전달할 키워드 인자

        Returns:
            함수의 반환값
        """
        return await async_retry(
            func,
            *args,
            retry_count=self.retry_count,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            backoff_factor=self.backoff_factor,
            retry_exceptions=self.retry_exceptions,
            retry_on_result=self.retry_on_result,
            **kwargs
        )
    
    def decorator(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        설정된 재시도 정책으로 데코레이터를 반환합니다.

        Returns:
            데코레이터 함수
        """
        return async_retry_decorator(
            retry_count=self.retry_count,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            backoff_factor=self.backoff_factor,
            retry_exceptions=self.retry_exceptions,
            retry_on_result=self.retry_on_result
        ) 