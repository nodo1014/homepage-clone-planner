"""
OpenAIClient 테스트

이 모듈은 OpenAIClient 클래스의 기능을 테스트합니다.
"""
import pytest
import os
import asyncio
import base64
from unittest.mock import patch, AsyncMock, MagicMock, mock_open, PropertyMock
from pathlib import Path
from src.api.openai_client import OpenAIClient


@pytest.fixture
def openai_client():
    """OpenAIClient 인스턴스를 생성하는 fixture"""
    with patch('os.getenv', return_value='test_key'):
        client = OpenAIClient()
    return client


@pytest.mark.asyncio
async def test_init_with_api_key():
    """API 키를 생성자에 전달했을 때 초기화 테스트"""
    client = OpenAIClient(api_key="provided_key")
    assert client.api_key == "provided_key"
    assert client.base_url == "https://api.openai.com/v1"


@pytest.mark.asyncio
async def test_init_without_api_key():
    """API 키를 전달하지 않았을 때 환경변수에서 가져오는지 테스트"""
    with patch('os.getenv', return_value='env_key'):
        client = OpenAIClient()
        assert client.api_key == "env_key"
        assert client.base_url == "https://api.openai.com/v1"


@pytest.mark.asyncio
async def test_validate_api_key_success(openai_client):
    """성공적인 API 키 유효성 검증 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (True, {"data": "success"})
        
        # API 키 유효성 검증 실행
        result = await openai_client.validate_api_key()
        
        # 결과 검증
        assert result is True
        mock_request.assert_called_once_with(
            method="GET",
            endpoint="/models"
        )


@pytest.mark.asyncio
async def test_validate_api_key_failure(openai_client):
    """실패한 API 키 유효성 검증 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (False, {"error": "Invalid API key"})
        
        # API 키 유효성 검증 실행
        result = await openai_client.validate_api_key()
        
        # 결과 검증
        assert result is False
        mock_request.assert_called_once_with(
            method="GET",
            endpoint="/models"
        )


@pytest.mark.asyncio
async def test_generate_text_success(openai_client):
    """성공적인 텍스트 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (True, {
            "choices": [
                {
                    "message": {
                        "content": "생성된 텍스트"
                    }
                }
            ]
        })
        
        # 텍스트 생성 실행
        success, text = await openai_client.generate_text(
            prompt="테스트 프롬프트",
            model="gpt-3.5-turbo",
            max_tokens=100
        )
        
        # 결과 검증
        assert success is True
        assert text == "생성된 텍스트"
        
        # 모킹된 request 메소드가 올바른 인자로 호출되었는지 검증
        mock_request.assert_called_once()
        # call_args는 (args, kwargs) 튜플을 반환하므로 kwargs만 검증
        _, kwargs = mock_request.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["endpoint"] == "/chat/completions"
        assert kwargs["data"]["model"] == "gpt-3.5-turbo"
        assert kwargs["data"]["messages"][1]["content"] == "테스트 프롬프트"
        assert kwargs["data"]["max_tokens"] == 100


@pytest.mark.asyncio
async def test_generate_text_failure(openai_client):
    """실패한 텍스트 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (False, {"error": "API 오류"})
        
        # 텍스트 생성 실행
        success, error = await openai_client.generate_text(
            prompt="테스트 프롬프트"
        )
        
        # 결과 검증
        assert success is False
        assert error == {"error": "API 오류"}


@pytest.mark.asyncio
async def test_generate_text_empty_response(openai_client):
    """응답에 텍스트가 없는 경우의 텍스트 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (True, {"choices": [{"message": {}}]})
        
        # 텍스트 생성 실행
        success, error = await openai_client.generate_text(
            prompt="테스트 프롬프트"
        )
        
        # 결과 검증
        assert success is False
        assert error == {"error": "텍스트 생성에 실패했습니다."}


@pytest.mark.asyncio
async def test_generate_image_success_url(openai_client):
    """URL 형식으로 성공적인 이미지 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (True, {
            "data": [
                {"url": "https://example.com/image1.png"},
                {"url": "https://example.com/image2.png"}
            ]
        })
        
        # 이미지 생성 실행
        success, images = await openai_client.generate_image(
            prompt="테스트 이미지",
            size="1024x1024",
            n=2
        )
        
        # 결과 검증
        assert success is True
        assert len(images) == 2
        assert images[0]["url"] == "https://example.com/image1.png"
        assert images[1]["url"] == "https://example.com/image2.png"
        
        # 모킹된 request 메소드가 올바른 인자로 호출되었는지 검증
        mock_request.assert_called_once()
        # call_args는 (args, kwargs) 튜플을 반환하므로 kwargs만 검증
        _, kwargs = mock_request.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["endpoint"] == "/images/generations"
        assert kwargs["data"]["model"] == "dall-e-3"
        assert kwargs["data"]["prompt"] == "테스트 이미지"
        assert kwargs["data"]["size"] == "1024x1024"
        assert kwargs["data"]["n"] == 2
        assert kwargs["data"]["response_format"] == "url"


@pytest.mark.asyncio
async def test_generate_image_success_b64(openai_client):
    """Base64 형식으로 성공적인 이미지 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (True, {
            "data": [
                {"b64_json": "base64_image_data"}
            ]
        })
        
        # _save_image 메소드를 모킹
        with patch.object(openai_client, '_save_image') as mock_save_image:
            mock_save_image.return_value = "/path/to/saved/image.png"
            
            # 이미지 생성 실행
            success, images = await openai_client.generate_image(
                prompt="테스트 이미지",
                output_dir="/output"
            )
            
            # 결과 검증
            assert success is True
            assert len(images) == 1
            assert images[0]["file_path"] == "/path/to/saved/image.png"
            
            # _save_image가 올바른 인자로 호출되었는지 검증
            mock_save_image.assert_called_once_with(
                "base64_image_data", 
                "/output", 
                "dalle_1.png"
            )


@pytest.mark.asyncio
async def test_generate_image_failure(openai_client):
    """실패한 이미지 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (False, {"error": "API 오류"})
        
        # 이미지 생성 실행
        success, error = await openai_client.generate_image(
            prompt="테스트 이미지"
        )
        
        # 결과 검증
        assert success is False
        assert error == {"error": "API 오류"}


@pytest.mark.asyncio
async def test_generate_image_empty_response(openai_client):
    """응답에 이미지가 없는 경우의 이미지 생성 테스트"""
    # request 메소드를 모킹
    with patch.object(openai_client, 'request') as mock_request:
        mock_request.return_value = (True, {"data": []})
        
        # 이미지 생성 실행
        success, error = await openai_client.generate_image(
            prompt="테스트 이미지"
        )
        
        # 결과 검증
        assert success is False
        assert error == {"error": "이미지 생성에 실패했습니다."}


def test_save_image(openai_client):
    """이미지 저장 테스트"""
    # mock_path 객체 생성 및 설정
    mock_path = MagicMock()
    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    
    # file_path = output_path / filename 연산의 결과 모킹
    file_path_mock = MagicMock()
    file_path_mock.__str__.return_value = "/output/dir/test_image.png"
    mock_path_instance.__truediv__.return_value = file_path_mock
    
    # Path 클래스 자체를 모킹
    with patch('src.api.openai_client.Path', mock_path):
        # base64.b64decode 함수를 모킹
        with patch('base64.b64decode', return_value=b'decoded_image_data'):
            # 파일 쓰기 모킹
            with patch('builtins.open', mock_open()) as mock_file:
                # 이미지 저장 실행
                result = openai_client._save_image(
                    "base64_encoded_data",
                    "/output/dir",
                    "test_image.png"
                )
                
                # 결과 검증 - 모킹된 경로 문자열과 일치해야 함
                assert result == "/output/dir/test_image.png"
                
                # 모킹된 함수들이 올바르게 호출되었는지 검증
                mock_path.assert_called_once_with("/output/dir")
                mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                
                # Path의 __truediv__ 연산자 (/연산) 검증
                mock_path_instance.__truediv__.assert_called_once_with("test_image.png")
                
                # open이 정확한 경로로 호출되었는지 검증
                mock_file.assert_called_once_with(file_path_mock, "wb") 