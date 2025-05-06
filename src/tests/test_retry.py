"""
재시도 메커니즘 테스트

이 모듈은 비동기 재시도 메커니즘에 대한 테스트를 제공합니다.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.utils.retry import async_retry, async_retry_decorator, RetryConfig, DEFAULT_RETRY_EXCEPTIONS


@pytest.mark.asyncio
async def test_async_retry_success_first_attempt():
    """첫 번째 시도에서 성공하는 경우 테스트"""
    # 모킹된 함수 생성
    mock_func = AsyncMock(return_value="성공")
    
    # async_retry 실행
    result = await async_retry(mock_func, "arg1", kwarg1="kwarg1")
    
    # 결과 검증
    assert result == "성공"
    # 함수가 한 번만 호출되었는지 확인
    mock_func.assert_called_once_with("arg1", kwarg1="kwarg1")


@pytest.mark.asyncio
async def test_async_retry_success_after_retries():
    """몇 번의 실패 후 성공하는 경우 테스트"""
    # 2번의 실패 후 성공하는 함수 모킹
    side_effects = [
        ConnectionError("연결 오류"),  # 첫 번째 시도: 실패
        TimeoutError("시간 초과"),     # 두 번째 시도: 실패
        "성공"                         # 세 번째 시도: 성공
    ]
    mock_func = AsyncMock(side_effect=side_effects)
    
    # retry_count를 조정하여 세 번째 시도까지 허용
    result = await async_retry(
        mock_func, 
        "arg1", 
        retry_count=3,
        base_delay=0.01,  # 테스트 속도를 위해 지연 시간 최소화
        kwarg1="kwarg1"
    )
    
    # 결과 검증
    assert result == "성공"
    # 함수가 세 번 호출되었는지 확인
    assert mock_func.call_count == 3
    # 모든 호출이 동일한 인자로 이루어졌는지 확인
    for call in mock_func.call_args_list:
        args, kwargs = call
        assert args == ("arg1",)
        assert kwargs == {"kwarg1": "kwarg1"}


@pytest.mark.asyncio
async def test_async_retry_all_attempts_fail():
    """모든 재시도가 실패하는 경우 테스트"""
    # 항상 실패하는 함수 모킹
    mock_func = AsyncMock(side_effect=ConnectionError("연결 오류"))
    
    # 3번의 시도 후 실패
    with pytest.raises(ConnectionError, match="연결 오류"):
        await async_retry(
            mock_func, 
            retry_count=2,
            base_delay=0.01  # 테스트 속도를 위해 지연 시간 최소화
        )
    
    # 함수가 3번 호출되었는지 확인 (초기 시도 + 2번의 재시도)
    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_async_retry_custom_exceptions():
    """사용자 정의 예외에 대한 재시도 테스트"""
    # 사용자 정의 예외 클래스
    class CustomError(Exception):
        pass
    
    # CustomError 발생 후 성공하는 함수 모킹
    side_effects = [
        CustomError("사용자 정의 오류"),  # 첫 번째 시도: 실패
        "성공"                           # 두 번째 시도: 성공
    ]
    mock_func = AsyncMock(side_effect=side_effects)
    
    # CustomError에 대해서만 재시도
    result = await async_retry(
        mock_func, 
        retry_count=1,
        base_delay=0.01,
        retry_exceptions=(CustomError,)
    )
    
    # 결과 검증
    assert result == "성공"
    assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_async_retry_on_result():
    """결과 값에 따른 재시도 테스트"""
    # 처음에는 재시도가 필요한 결과 반환, 두 번째는 성공 결과 반환
    side_effects = [
        {"status": "error", "retry": True},  # 첫 번째 시도: 재시도 필요
        {"status": "success", "retry": False}  # 두 번째 시도: 성공
    ]
    mock_func = AsyncMock(side_effect=side_effects)
    
    # 결과를 검사하여 재시도 여부 결정하는 함수
    def retry_on_result(result):
        return result.get("retry", False)
    
    # 결과 검사 기반 재시도
    result = await async_retry(
        mock_func, 
        retry_count=1,
        base_delay=0.01,
        retry_on_result=retry_on_result
    )
    
    # 결과 검증
    assert result == {"status": "success", "retry": False}
    assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_async_retry_decorator():
    """재시도 데코레이터 테스트"""
    side_effects = [
        ConnectionError("연결 오류"),  # 첫 번째 시도: 실패
        "성공"                         # 두 번째 시도: 성공
    ]
    mock_func = AsyncMock(side_effect=side_effects)
    
    # 데코레이터 생성 및 적용
    decorator = async_retry_decorator(
        retry_count=1,
        base_delay=0.01
    )
    decorated_func = decorator(mock_func)
    
    # 데코레이터가 적용된 함수 호출
    result = await decorated_func("arg1", kwarg1="kwarg1")
    
    # 결과 검증
    assert result == "성공"
    assert mock_func.call_count == 2
    # 모든 호출이 동일한 인자로 이루어졌는지 확인
    for call in mock_func.call_args_list:
        args, kwargs = call
        assert args == ("arg1",)
        assert kwargs == {"kwarg1": "kwarg1"}


@pytest.mark.asyncio
async def test_retry_config():
    """RetryConfig 클래스 테스트"""
    # 구성 설정
    config = RetryConfig(
        retry_count=2,
        base_delay=0.01,
        max_delay=0.1,
        backoff_factor=2.0
    )
    
    # 2번의 실패 후 성공하는 함수 모킹
    side_effects = [
        ConnectionError("첫 번째 오류"),
        TimeoutError("두 번째 오류"),
        "성공"
    ]
    mock_func = AsyncMock(side_effect=side_effects)
    
    # RetryConfig.retry 메서드로 실행
    result = await config.retry(mock_func, "arg1", kwarg1="kwarg1")
    
    # 결과 검증
    assert result == "성공"
    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_retry_config_decorator():
    """RetryConfig 데코레이터 테스트"""
    # 구성 설정
    config = RetryConfig(
        retry_count=1,
        base_delay=0.01
    )
    
    # 함수 모킹
    side_effects = [
        ConnectionError("연결 오류"),
        "성공"
    ]
    mock_func = AsyncMock(side_effect=side_effects)
    
    # config.decorator()로 데코레이터 생성 및 적용
    decorator = config.decorator()
    decorated_func = decorator(mock_func)
    
    # 데코레이터가 적용된 함수 호출
    result = await decorated_func()
    
    # 결과 검증
    assert result == "성공"
    assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_backoff_timing():
    """지수 백오프 타이밍 테스트"""
    # sleep 함수를 모킹하여 지연 시간 확인
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # 항상 예외를 발생시키는 함수
        mock_func = AsyncMock(side_effect=ConnectionError("연결 오류"))
        
        # 재시도 설정 (2번의 재시도, 지수 백오프)
        try:
            await async_retry(
                mock_func,
                retry_count=2,
                base_delay=1.0,
                backoff_factor=2.0
            )
        except ConnectionError:
            pass  # 예외는 예상된 동작
        
        # asyncio.sleep 호출 확인
        assert mock_sleep.call_count == 2
        
        # 첫 번째 재시도: base_delay인 1.0초 지연
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        
        # 두 번째 재시도: base_delay * backoff_factor = 1.0 * 2.0 = 2.0초 지연
        assert mock_sleep.call_args_list[1][0][0] == 2.0


@pytest.mark.asyncio
async def test_max_delay_limit():
    """최대 지연 시간 제한 테스트"""
    # sleep 함수를 모킹하여 지연 시간 확인
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # 항상 예외를 발생시키는 함수
        mock_func = AsyncMock(side_effect=ConnectionError("연결 오류"))
        
        # 재시도 설정 (3번의 재시도, 최대 지연 시간 2.0초)
        try:
            await async_retry(
                mock_func,
                retry_count=3,
                base_delay=1.0,
                max_delay=2.0,
                backoff_factor=3.0
            )
        except ConnectionError:
            pass  # 예외는 예상된 동작
        
        # asyncio.sleep 호출 확인
        assert mock_sleep.call_count == 3
        
        # 첫 번째 재시도: 1.0초 지연
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        
        # 두 번째 재시도: 3.0초 계산되지만 max_delay인 2.0초로 제한
        assert mock_sleep.call_args_list[1][0][0] == 2.0
        
        # 세 번째 재시도: 9.0초 계산되지만 max_delay인 2.0초로 제한
        assert mock_sleep.call_args_list[2][0][0] == 2.0 