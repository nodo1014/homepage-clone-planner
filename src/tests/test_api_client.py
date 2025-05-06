"""
BaseAPIClient 테스트

이 모듈은 BaseAPIClient 클래스 및 관련 팩토리 함수를 테스트합니다.
"""
import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.api.api_client import BaseAPIClient, create_api_client, create_api_client_by_mode


@pytest.fixture
def base_api_client():
    """BaseAPIClient 인스턴스를 생성하는 fixture"""
    client = BaseAPIClient(api_key="test_key", base_url="https://api.example.com")
    return client


@pytest.mark.asyncio
async def test_request_success(base_api_client):
    """성공적인 API 요청 테스트"""
    # 모킹된 응답 생성
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"result": "success"}
    mock_response.raise_for_status = lambda: None
    
    # client.request 메소드를 모킹
    async def mock_client_request(*args, **kwargs):
        return mock_response
    
    # base_api_client.client.request를 모킹
    with patch.object(base_api_client.client, 'request', side_effect=mock_client_request):
        # API 요청 실행
        success, data = await base_api_client.request(
            method="GET",
            endpoint="/test",
            data={"key": "value"},
            headers={"Custom-Header": "Value"}
        )
        
        # 결과 검증
        assert success is True
        assert data == {"result": "success"}
        
        # 모킹된 request 메소드가 올바른 인자로 호출되었는지 검증
        base_api_client.client.request.assert_called_once()
        args, kwargs = base_api_client.client.request.call_args
        assert args[0] == "GET"
        assert args[1] == "https://api.example.com/test"
        assert kwargs["json"] == {"key": "value"}
        assert kwargs["headers"] == {"Custom-Header": "Value", "Authorization": "Bearer test_key"}


@pytest.mark.asyncio
async def test_request_http_error(base_api_client):
    """HTTP 오류 발생 시 API 요청 테스트"""
    import httpx
    
    # 모킹된 응답 및 오류 설정
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"error": "Resource not found"}
    
    # HTTPStatusError를 발생시키는 raise_for_status 메소드
    def raise_status_error():
        error = httpx.HTTPStatusError(
            "404 Not Found", 
            request=httpx.Request("GET", "https://example.com"), 
            response=mock_response
        )
        error.response = mock_response  # 오류 객체에 응답 설정
        raise error
    
    mock_response.raise_for_status = raise_status_error
    
    # client.request 메소드를 모킹
    async def mock_client_request(*args, **kwargs):
        return mock_response
    
    # base_api_client.client.request를 모킹
    with patch.object(base_api_client.client, 'request', side_effect=mock_client_request):
        # API 요청 실행
        success, data = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 결과 검증
        assert success is False
        assert "error" in data
        assert data["error"] == "Resource not found"


@pytest.mark.asyncio
async def test_request_network_error(base_api_client):
    """네트워크 오류 발생 시 API 요청 테스트"""
    import httpx
    
    # client.request 메소드를 모킹하여 RequestError 발생
    async def mock_client_request_error(*args, **kwargs):
        raise httpx.RequestError("Connection error", request=httpx.Request("GET", "https://example.com"))
    
    # base_api_client.client.request를 모킹
    with patch.object(base_api_client.client, 'request', side_effect=mock_client_request_error):
        # API 요청 실행
        success, data = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 결과 검증
        assert success is False
        assert "error" in data
        assert data["error"] == "네트워크 오류"


@pytest.mark.asyncio
async def test_validate_api_key_not_implemented(base_api_client):
    """validate_api_key 메소드가 NotImplementedError를 발생시키는지 테스트"""
    with pytest.raises(NotImplementedError):
        await base_api_client.validate_api_key()


@pytest.mark.asyncio
async def test_close(base_api_client):
    """client.aclose 호출이 잘 되는지 테스트"""
    # httpx.AsyncClient.aclose 메소드를 모킹
    with patch.object(base_api_client.client, 'aclose') as mock_aclose:
        # aclose 호출
        await base_api_client.close()
        
        # 모킹된 aclose가 호출되었는지 검증
        mock_aclose.assert_called_once()


@pytest.mark.asyncio
async def test_create_api_client():
    """create_api_client 함수가 올바른 API 클라이언트를 생성하는지 테스트"""
    # OpenAIClient 및 ClaudeClient 클래스를 모킹하기 위한 설정
    with patch('src.api.openai_client.OpenAIClient') as mock_openai, \
         patch('src.api.anthropic_client.ClaudeClient') as mock_claude, \
         patch('src.api.ollama_client.OllamaClient') as mock_ollama, \
         patch('src.api.stable_diffusion_client.StableDiffusionClient') as mock_sd:
        
        # 각 모킹된 클래스가 인스턴스를 반환하도록 설정
        mock_openai.return_value = "openai_client_instance"
        mock_claude.return_value = "claude_client_instance"
        mock_ollama.return_value = "ollama_client_instance"
        mock_sd.return_value = "stable_diffusion_client_instance"
        
        # 테스트 config 생성
        config = {
            "api_keys": {
                "dalle": "dalle_api_key",
                "claude": "claude_api_key"
            },
            "api": {
                "local_ollama_url": "http://localhost:11434",
                "local_sd_url": "http://localhost:7860"
            }
        }
        
        # 각 API 타입에 대해 create_api_client 호출
        openai_client = create_api_client("openai", config)
        claude_client = create_api_client("anthropic", config)
        ollama_client = create_api_client("ollama", config)
        sd_client = create_api_client("stable_diffusion", config)
        
        # 결과 검증
        assert openai_client == "openai_client_instance"
        assert claude_client == "claude_client_instance"
        assert ollama_client == "ollama_client_instance"
        assert sd_client == "stable_diffusion_client_instance"
        
        # 각 클래스가 올바른 인자로 초기화되었는지 검증
        mock_openai.assert_called_once_with(api_key="dalle_api_key")
        mock_claude.assert_called_once_with(api_key="claude_api_key")
        mock_ollama.assert_called_once_with(api_url="http://localhost:11434")
        mock_sd.assert_called_once_with(api_url="http://localhost:7860")


@pytest.mark.asyncio
async def test_create_api_client_unknown_type():
    """알 수 없는 API 타입에 대한 처리 테스트"""
    # 알 수 없는 API 타입으로 create_api_client 호출
    client = create_api_client("unknown_type", {})
    
    # 결과가 BaseAPIClient 인스턴스인지 검증
    assert isinstance(client, BaseAPIClient) 


# 재시도 메커니즘 테스트 추가
@pytest.mark.asyncio
async def test_request_retry_on_network_error(base_api_client):
    """네트워크 오류 시 재시도 메커니즘 테스트"""
    import httpx
    
    # 처음 2번은 실패, 3번째 시도에서 성공하는 모킹
    side_effects = [
        httpx.RequestError("Connection error 1", request=httpx.Request("GET", "https://example.com")),
        httpx.RequestError("Connection error 2", request=httpx.Request("GET", "https://example.com")),
        MagicMock(status_code=200, headers={"Content-Type": "application/json"})
    ]
    
    # 성공 응답 설정
    success_response = side_effects[2]
    success_response.json.return_value = {"result": "success after retry"}
    success_response.raise_for_status = lambda: None
    
    # request 구현 메소드를 직접 모킹
    with patch.object(base_api_client, '_request_impl') as mock_request_impl:
        # 첫 두 번은 예외 발생, 세 번째는 성공
        mock_request_impl.side_effect = [
            (False, {"error": "Connection error 1"}),
            (False, {"error": "Connection error 2"}),
            (True, {"result": "success after retry"})
        ]
        
        # 재시도 설정 - 더 빠른 테스트를 위해 지연 시간 최소화
        base_api_client.set_retry_config(
            retry_count=2,  # 최대 2번 재시도
            base_delay=0.01  # 지연 시간 최소화
        )
        
        # API 요청 실행
        success, data = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 결과 검증
        assert success is True
        assert data["result"] == "success after retry"
        
        # 정확히 3번 호출되었는지 확인 (초기 + 2번 재시도)
        assert mock_request_impl.call_count == 3
        
        # 모든 호출이 동일한 인자로 이루어졌는지 확인
        for call in mock_request_impl.call_args_list:
            args, kwargs = call
            assert kwargs["method"] == "GET"
            assert kwargs["endpoint"] == "/test"


@pytest.mark.asyncio
async def test_request_retry_on_server_error(base_api_client):
    """서버 오류(5xx) 시 재시도 메커니즘 테스트"""
    import httpx
    
    # 500 서버 오류 응답 생성
    error_response = MagicMock()
    error_response.status_code = 500
    error_response.headers = {"Content-Type": "application/json"}
    error_response.json.return_value = {"error": "Internal Server Error"}
    
    # 성공 응답 생성
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.headers = {"Content-Type": "application/json"}
    success_response.json.return_value = {"result": "success after retry"}
    success_response.raise_for_status = lambda: None
    
    # 서버 오류 발생시키는 함수
    def raise_server_error():
        error = httpx.HTTPStatusError(
            "500 Internal Server Error", 
            request=httpx.Request("GET", "https://example.com"), 
            response=error_response
        )
        error.response = error_response
        raise error
    
    # 첫 응답은 500 오류 설정
    error_response.raise_for_status = raise_server_error
    
    # request 구현 메소드를 직접 모킹
    with patch.object(base_api_client, '_request_impl') as mock_request_impl:
        # 첫 번째는 500 오류, 두 번째는 성공
        mock_request_impl.side_effect = [
            (False, {"error": "Internal Server Error", "status_code": 500}),
            (True, {"result": "success after retry"})
        ]
        
        # 재시도 설정 - 더 빠른 테스트를 위해 지연 시간 최소화
        base_api_client.set_retry_config(
            retry_count=1,  # 최대 1번 재시도
            base_delay=0.01  # 지연 시간 최소화
        )
        
        # API 요청 실행
        success, data = await base_api_client.request(
            method="POST",
            endpoint="/test",
            data={"test": "data"}
        )
        
        # 결과 검증
        assert success is True
        assert data["result"] == "success after retry"
        
        # 정확히 2번 호출되었는지 확인 (초기 + 1번 재시도)
        assert mock_request_impl.call_count == 2


@pytest.mark.asyncio
async def test_request_retry_on_rate_limit(base_api_client):
    """Rate Limit(429) 오류 시 재시도 메커니즘 테스트"""
    import httpx
    
    # request 구현 메소드를 직접 모킹
    with patch.object(base_api_client, '_request_impl') as mock_request_impl:
        # 첫 번째는 429 오류, 두 번째는 성공
        mock_request_impl.side_effect = [
            (False, {"error": "Too Many Requests", "status_code": 429}),
            (True, {"result": "success after rate limit"})
        ]
        
        # 재시도 설정 - 더 빠른 테스트를 위해 지연 시간 최소화
        base_api_client.set_retry_config(
            retry_count=1,  # 최대 1번 재시도
            base_delay=0.01  # 지연 시간 최소화
        )
        
        # API 요청 실행
        success, data = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 결과 검증
        assert success is True
        assert data["result"] == "success after rate limit"
        
        # 정확히 2번 호출되었는지 확인 (초기 + 1번 재시도)
        assert mock_request_impl.call_count == 2


@pytest.mark.asyncio
async def test_request_max_retries_reached(base_api_client):
    """최대 재시도 횟수 도달 시 테스트"""
    import httpx
    
    # request 구현 메소드를 직접 모킹
    with patch.object(base_api_client, '_request_impl') as mock_request_impl:
        # 모든 시도에서 네트워크 오류 발생
        mock_request_impl.side_effect = [
            (False, {"error": "Connection error 1"}),
            (False, {"error": "Connection error 2"}),
            (False, {"error": "Connection error 3"})
        ]
        
        # 재시도 설정 - 더 빠른 테스트를 위해 지연 시간 최소화
        base_api_client.set_retry_config(
            retry_count=2,  # 최대 2번 재시도
            base_delay=0.01  # 지연 시간 최소화
        )
        
        # API 요청 실행
        success, data = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 결과 검증 - 모든 재시도 후에도 실패
        assert success is False
        assert data["error"] == "Connection error 3"
        
        # 정확히 3번 호출되었는지 확인 (초기 + 2번 재시도)
        assert mock_request_impl.call_count == 3


@pytest.mark.asyncio
async def test_set_retry_config(base_api_client):
    """재시도 설정 변경 테스트"""
    # 초기 설정 확인
    assert base_api_client.retry_config.retry_count == 3
    assert base_api_client.retry_config.base_delay == 1.0
    assert base_api_client.retry_config.max_delay == 10.0
    assert base_api_client.retry_config.backoff_factor == 2.0
    
    # 설정 변경
    base_api_client.set_retry_config(
        retry_count=5,
        base_delay=0.5,
        max_delay=5.0,
        backoff_factor=1.5
    )
    
    # 변경된 설정 확인
    assert base_api_client.retry_config.retry_count == 5
    assert base_api_client.retry_config.base_delay == 0.5
    assert base_api_client.retry_config.max_delay == 5.0
    assert base_api_client.retry_config.backoff_factor == 1.5
    
    # 일부만 변경
    base_api_client.set_retry_config(
        retry_count=2
    )
    
    # 일부만 변경된 설정 확인
    assert base_api_client.retry_config.retry_count == 2
    assert base_api_client.retry_config.base_delay == 0.5  # 이전 값 유지
    assert base_api_client.retry_config.max_delay == 5.0  # 이전 값 유지
    assert base_api_client.retry_config.backoff_factor == 1.5  # 이전 값 유지


# =========== 캐시 기능 테스트 추가 ===========
@pytest.mark.asyncio
async def test_api_client_caching(base_api_client):
    """BaseAPIClient의 캐싱 기능 테스트"""
    # _direct_request 메소드를 직접 모킹
    with patch.object(base_api_client, '_direct_request', 
                    return_value=(True, {"result": "test_data"})) as mock_direct_request:
        # 첫 번째 요청 (캐시 미스)
        success1, data1 = await base_api_client.request(
            method="GET",
            endpoint="/test",
            params={"param": "value"}
        )
        
        # 두 번째 요청 (동일 파라미터, 캐시 히트)
        success2, data2 = await base_api_client.request(
            method="GET",
            endpoint="/test",
            params={"param": "value"}
        )
        
        # 세 번째 요청 (다른 파라미터, 캐시 미스)
        success3, data3 = await base_api_client.request(
            method="GET",
            endpoint="/test",
            params={"param": "different"}
        )
        
        # 네 번째 요청 (POST, 캐싱 안 함)
        success4, data4 = await base_api_client.request(
            method="POST",
            endpoint="/test",
            data={"key": "value"}
        )
        
        # 결과 검증
        assert success1 is True
        assert success2 is True
        assert success3 is True
        assert success4 is True
        
        assert data1 == data2 == data3 == data4
        
        # 요청 횟수 검증 (캐시 히트로 인해 3번만 호출되어야 함)
        # 첫 번째 GET + 세 번째 GET (다른 파라미터) + POST 요청
        assert mock_direct_request.call_count == 3
        
        # 호출 파라미터 검증
        call_args_list = mock_direct_request.call_args_list
        
        # 첫 번째 요청
        args, kwargs = call_args_list[0]
        assert kwargs["method"] == "GET"
        assert kwargs["endpoint"] == "/test"
        assert kwargs["params"] == {"param": "value"}
        
        # 세 번째 요청 (두 번째는 캐시 히트)
        args, kwargs = call_args_list[1]
        assert kwargs["method"] == "GET"
        assert kwargs["endpoint"] == "/test"
        assert kwargs["params"] == {"param": "different"}
        
        # 네 번째 요청 (POST 요청)
        args, kwargs = call_args_list[2]
        assert kwargs["method"] == "POST"
        assert kwargs["endpoint"] == "/test"
        assert kwargs["data"] == {"key": "value"}


@pytest.mark.asyncio
async def test_api_client_cache_disabled(base_api_client):
    """캐싱 비활성화 테스트"""
    # 캐싱 비활성화
    base_api_client.use_cache = False
    
    # _direct_request 메소드를 직접 모킹
    with patch.object(base_api_client, '_direct_request', 
                    return_value=(True, {"result": "test_data"})) as mock_direct_request:
        # 첫 번째 요청
        success1, data1 = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 두 번째 요청 (동일 요청이지만 캐싱 비활성화로 인해 캐시 미스)
        success2, data2 = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 결과 검증
        assert success1 is True
        assert success2 is True
        assert data1 == data2
        
        # 캐싱이 비활성화되었으므로 두 번 모두 호출되어야 함
        assert mock_direct_request.call_count == 2


@pytest.mark.asyncio
async def test_api_client_cache_override(base_api_client):
    """요청별 캐싱 오버라이드 테스트"""
    # _direct_request 메소드를 직접 모킹
    with patch.object(base_api_client, '_direct_request', 
                    return_value=(True, {"result": "test_data"})) as mock_direct_request:
        # 첫 번째 요청 (기본 캐싱)
        success1, data1 = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 두 번째 요청 (캐싱 비활성화로 오버라이드)
        success2, data2 = await base_api_client.request(
            method="GET",
            endpoint="/test",
            use_cache=False
        )
        
        # 세 번째 요청 (기본 캐싱, 첫 번째와 동일)
        success3, data3 = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 결과 검증
        assert success1 is True
        assert success2 is True
        assert success3 is True
        
        # 요청 횟수 검증 (두 번째 요청은 캐싱 비활성화, 세 번째는 캐시 히트)
        assert mock_direct_request.call_count == 2


@pytest.mark.asyncio
async def test_api_client_clear_cache(base_api_client):
    """캐시 비우기 테스트"""
    # _direct_request 메소드를 직접 모킹 (실제 요청 처리부)
    with patch.object(base_api_client, '_direct_request', 
                    return_value=(True, {"result": "test_data"})) as mock_direct_request:
        # 첫 번째 요청
        success1, data1 = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 첫 번째 호출 검증
        assert mock_direct_request.call_count == 1
        mock_direct_request.reset_mock()  # 호출 카운트 리셋
        
        # 동일한 요청 다시 실행 (캐시 히트)
        success2, data2 = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 캐시 히트로 인해 추가 호출 없음
        assert mock_direct_request.call_count == 0
        
        # 캐시 비우기
        await base_api_client.clear_cache()
        
        # 세 번째 요청 (캐시가 비워져서 캐시 미스)
        success3, data3 = await base_api_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 캐시가 비워졌으므로 새로운 요청 발생
        assert mock_direct_request.call_count == 1
        
        # 결과 검증
        assert success1 is True
        assert success2 is True
        assert success3 is True
        assert data1 == data2 == data3


@pytest.mark.asyncio
async def test_api_client_cache_key_generation(base_api_client):
    """캐시 키 생성 테스트"""
    # 다양한 조합으로 캐시 키 생성
    key1 = base_api_client._build_cache_key("GET", "/endpoint")
    key2 = base_api_client._build_cache_key("GET", "/endpoint", {"param": "value"})
    key3 = base_api_client._build_cache_key("POST", "/endpoint")
    key4 = base_api_client._build_cache_key("GET", "/different")
    key5 = base_api_client._build_cache_key("GET", "/endpoint", {"param": "different"})
    key6 = base_api_client._build_cache_key("GET", "/endpoint", {"param": "value"})
    
    # 검증: 동일한 요청은 동일한 키를 생성
    assert key2 == key6
    
    # 검증: 다른 요청은 다른 키를 생성
    assert key1 != key2
    assert key2 != key3
    assert key2 != key4
    assert key2 != key5
    
    # 검증: 파라미터 순서는 영향을 주지 않음
    key_ordered = base_api_client._build_cache_key("GET", "/endpoint", {"a": 1, "b": 2})
    key_reverse = base_api_client._build_cache_key("GET", "/endpoint", {"b": 2, "a": 1})
    assert key_ordered == key_reverse


@pytest.mark.asyncio
async def test_api_client_cache_stats(base_api_client):
    """캐시 통계 기능 테스트"""
    # _direct_request 메소드를 직접 모킹
    with patch.object(base_api_client, '_direct_request', 
                    return_value=(True, {"result": "test_data"})) as mock_direct_request:
        # 여러 요청 실행
        await base_api_client.request(method="GET", endpoint="/test1")
        await base_api_client.request(method="GET", endpoint="/test2")
        await base_api_client.request(method="GET", endpoint="/test1")  # 캐시 히트
        
        # 통계 정보 가져오기
        stats = await base_api_client.get_cache_stats()
        
        # 검증
        assert "memory_cache" in stats
        assert "disk_cache" in stats
        
        # 메모리 캐시에 2개의 항목이 있어야 함 (중복 제외)
        memory_stats = stats["memory_cache"]
        assert memory_stats is not None
        assert memory_stats["total_items"] == 2
        
        # 캐싱 비활성화 테스트
        base_api_client.use_cache = False
        disabled_stats = await base_api_client.get_cache_stats()
        assert disabled_stats == {"enabled": False} 