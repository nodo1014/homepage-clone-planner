"""
ClaudeClient 테스트

이 모듈은 ClaudeClient 클래스의 기능을 테스트합니다.
"""
import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.api.anthropic_client import ClaudeClient
import httpx


@pytest.fixture
def claude_client():
    """ClaudeClient 인스턴스를 생성하는 fixture"""
    with patch('os.getenv', return_value='test_key'):
        client = ClaudeClient()
    return client


@pytest.mark.asyncio
async def test_init_with_api_key():
    """API 키를 생성자에 전달했을 때 초기화 테스트"""
    client = ClaudeClient(api_key="provided_key")
    assert client.api_key == "provided_key"
    assert client.base_url == "https://api.anthropic.com/v1"


@pytest.mark.asyncio
async def test_init_without_api_key():
    """API 키를 전달하지 않았을 때 환경변수에서 가져오는지 테스트"""
    with patch('os.getenv', return_value='env_key'):
        client = ClaudeClient()
        assert client.api_key == "env_key"
        assert client.base_url == "https://api.anthropic.com/v1"


@pytest.mark.asyncio
async def test_validate_api_key_success(claude_client):
    """성공적인 API 키 유효성 검증 테스트"""
    # generate_text 메소드를 모킹
    with patch.object(claude_client, 'generate_text') as mock_generate:
        mock_generate.return_value = (True, "테스트 응답")
        
        # API 키 유효성 검증 실행
        result = await claude_client.validate_api_key()
        
        # 결과 검증
        assert result is True
        mock_generate.assert_called_once_with("API 키 유효성 검증", max_tokens=10)


@pytest.mark.asyncio
async def test_validate_api_key_failure(claude_client):
    """실패한 API 키 유효성 검증 테스트"""
    # generate_text 메소드를 모킹
    with patch.object(claude_client, 'generate_text') as mock_generate:
        mock_generate.return_value = (False, {"error": "Invalid API key"})
        
        # API 키 유효성 검증 실행
        result = await claude_client.validate_api_key()
        
        # 결과 검증
        assert result is False
        mock_generate.assert_called_once_with("API 키 유효성 검증", max_tokens=10)


@pytest.mark.asyncio
async def test_request_method(claude_client):
    """오버라이드된 request 메소드 테스트"""
    # 모킹된 응답 객체 생성
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"result": "success"}
    mock_response.raise_for_status = lambda: None
    
    # httpx.AsyncClient.request를 모킹하여 모킹된 응답 반환
    async def mock_client_request(*args, **kwargs):
        return mock_response
    
    # claude_client.client.request 메소드를 모킹
    with patch.object(claude_client.client, 'request', side_effect=mock_client_request):
        # 오버라이드된 request 메소드 호출
        success, result = await claude_client.request(
            method="POST",
            endpoint="/test",
            data={"key": "value"},
            headers={"Custom-Header": "Value"}
        )
        
        # 결과 검증
        assert success is True
        assert result == {"result": "success"}
        
        # 메소드가 올바른 인자로 호출되었는지 검증
        claude_client.client.request.assert_called_once()
        args, kwargs = claude_client.client.request.call_args
        
        assert args[0] == "POST"
        assert args[1] == "https://api.anthropic.com/v1/test"  # 전체 URL 확인
        assert kwargs["json"] == {"key": "value"}
        
        # Claude 특화 헤더가 추가되었는지 검증
        assert "x-api-key" in kwargs["headers"]
        assert kwargs["headers"]["x-api-key"] == "test_key"
        assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert "Custom-Header" in kwargs["headers"]


@pytest.mark.asyncio
async def test_request_no_headers(claude_client):
    """헤더를 지정하지 않은 경우의 request 메소드 테스트"""
    # 모킹된 응답 객체 생성
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"result": "success"}
    mock_response.raise_for_status = lambda: None
    
    # httpx.AsyncClient.request를 모킹하여 모킹된 응답 반환
    async def mock_client_request(*args, **kwargs):
        return mock_response
    
    # claude_client.client.request 메소드를 모킹
    with patch.object(claude_client.client, 'request', side_effect=mock_client_request):
        # 헤더 없이 request 메소드 호출
        success, result = await claude_client.request(
            method="GET",
            endpoint="/test"
        )
        
        # 결과 검증
        assert success is True
        
        # 메소드가 올바른 인자로 호출되었는지 검증
        claude_client.client.request.assert_called_once()
        args, kwargs = claude_client.client.request.call_args
        
        # 헤더에 기본값들이 설정되었는지 확인
        assert "headers" in kwargs
        assert kwargs["headers"]["x-api-key"] == "test_key"
        assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
        assert kwargs["headers"]["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_request_existing_headers(claude_client):
    """기존 헤더를 덮어쓰지 않는지 테스트"""
    # 모킹된 응답 객체 생성
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"result": "success"}
    mock_response.raise_for_status = lambda: None
    
    # httpx.AsyncClient.request를 모킹하여 모킹된 응답 반환
    async def mock_client_request(*args, **kwargs):
        return mock_response
    
    # claude_client.client.request 메소드를 모킹
    with patch.object(claude_client.client, 'request', side_effect=mock_client_request):
        # 사용자 지정 헤더로 request 메소드 호출
        success, result = await claude_client.request(
            method="GET",
            endpoint="/test",
            headers={
                "x-api-key": "user_key",
                "anthropic-version": "custom_version",
                "Content-Type": "application/xml",
                "Custom-Header": "Value"
            }
        )
        
        # 결과 검증
        assert success is True
        
        # 메소드가 올바른 인자로 호출되었는지 검증
        claude_client.client.request.assert_called_once()
        args, kwargs = claude_client.client.request.call_args
        
        # 사용자 지정 헤더가 유지되었는지 확인
        assert kwargs["headers"]["x-api-key"] == "user_key"  # 사용자 지정값 유지
        assert kwargs["headers"]["anthropic-version"] == "custom_version"  # 사용자 지정값 유지
        assert kwargs["headers"]["Content-Type"] == "application/xml"  # 사용자 지정값 유지
        assert kwargs["headers"]["Custom-Header"] == "Value"  # 추가 헤더 유지


@pytest.mark.asyncio
async def test_generate_text_success(claude_client):
    """성공적인 텍스트 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(claude_client, 'request') as mock_request:
        mock_request.return_value = (True, {
            "content": [
                {
                    "type": "text",
                    "text": "생성된 텍스트 1"
                },
                {
                    "type": "text",
                    "text": "생성된 텍스트 2"
                }
            ]
        })
        
        # 텍스트 생성 실행
        success, text = await claude_client.generate_text(
            prompt="테스트 프롬프트",
            model="claude-3-opus-20240229",
            max_tokens=100
        )
        
        # 결과 검증
        assert success is True
        assert text == "생성된 텍스트 1생성된 텍스트 2"
        
        # 모킹된 request 메소드가 올바른 인자로 호출되었는지 검증
        mock_request.assert_called_once()
        # kwargs 파라미터 검증
        _, kwargs = mock_request.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["endpoint"] == "/messages"
        assert kwargs["data"]["model"] == "claude-3-opus-20240229"
        assert kwargs["data"]["messages"][0]["content"] == "테스트 프롬프트"
        assert kwargs["data"]["max_tokens"] == 100
        assert "x-api-key" in kwargs["headers"]
        assert kwargs["headers"]["anthropic-version"] == "2023-06-01"


@pytest.mark.asyncio
async def test_generate_text_failure(claude_client):
    """실패한 텍스트 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(claude_client, 'request') as mock_request:
        mock_request.return_value = (False, {"error": "API 오류"})
        
        # 텍스트 생성 실행
        success, error = await claude_client.generate_text(
            prompt="테스트 프롬프트"
        )
        
        # 결과 검증
        assert success is False
        assert error == {"error": "API 오류"}


@pytest.mark.asyncio
async def test_generate_text_empty_response(claude_client):
    """응답에 텍스트가 없는 경우의 텍스트 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(claude_client, 'request') as mock_request:
        mock_request.return_value = (True, {"content": []})
        
        # 텍스트 생성 실행
        success, error = await claude_client.generate_text(
            prompt="테스트 프롬프트"
        )
        
        # 결과 검증
        assert success is False
        assert error == {"error": "텍스트 생성에 실패했습니다."}


@pytest.mark.asyncio
async def test_generate_text_mixed_content(claude_client):
    """다양한 타입의 콘텐츠가 포함된 응답 처리 테스트"""
    # request 메소드를 모킹
    with patch.object(claude_client, 'request') as mock_request:
        mock_request.return_value = (True, {
            "content": [
                {
                    "type": "text",
                    "text": "텍스트 부분 1"
                },
                {
                    "type": "image",  # 이미지 타입은 무시되어야 함
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": "base64_data"
                    }
                },
                {
                    "type": "text",
                    "text": "텍스트 부분 2"
                }
            ]
        })
        
        # 텍스트 생성 실행
        success, text = await claude_client.generate_text(
            prompt="테스트 프롬프트"
        )
        
        # 결과 검증
        assert success is True
        assert text == "텍스트 부분 1텍스트 부분 2"  # 텍스트만 추출되어야 함 