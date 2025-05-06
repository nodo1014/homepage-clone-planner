"""
API 클라이언트 팩토리 테스트

이 모듈은 API 클라이언트 팩토리 함수(create_api_client_by_mode)를 테스트합니다.
"""
import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.api.api_client import create_api_client_by_mode


@pytest.mark.asyncio
async def test_create_api_client_by_mode_image_gen_paid():
    """유료 이미지 생성 API 클라이언트 생성 테스트"""
    # 모듈 및 클래스 모킹
    with patch('src.api.api_client.create_api_client') as mock_create_client:
        # 모킹된 API 클라이언트 설정
        mock_client = AsyncMock()
        mock_client.validate_api_key = AsyncMock(return_value=True)
        mock_create_client.return_value = mock_client
        
        # 테스트 설정
        config = {
            "api_keys": {"dalle": "test_key"},
            "api": {"image_gen_mode": "free"}  # 모드 설정과 관계없이 paid가 우선
        }
        
        # 함수 호출
        client = await create_api_client_by_mode("paid", "image_gen", config)
        
        # 검증
        mock_create_client.assert_called_once_with("openai", config)
        assert client == mock_client


@pytest.mark.asyncio
async def test_create_api_client_by_mode_image_gen_free():
    """무료 이미지 생성 API 클라이언트 생성 테스트"""
    # 모듈 및 클래스 모킹
    with patch('src.api.api_client.create_api_client') as mock_create_client:
        # 모킹된 API 클라이언트 설정
        mock_client = AsyncMock()
        mock_client.validate_api_connection = AsyncMock(return_value=True)
        mock_create_client.return_value = mock_client
        
        # 테스트 설정
        config = {
            "api": {"local_sd_url": "http://localhost:7860"}
        }
        
        # 함수 호출
        client = await create_api_client_by_mode("free", "image_gen", config)
        
        # 검증
        mock_create_client.assert_called_once_with("stable_diffusion", config)
        assert client == mock_client


@pytest.mark.asyncio
async def test_create_api_client_by_mode_idea_gen_paid():
    """유료 아이디어 생성 API 클라이언트 생성 테스트"""
    # 모듈 및 클래스 모킹
    with patch('src.api.api_client.create_api_client') as mock_create_client:
        # 모킹된 API 클라이언트 설정
        mock_client = AsyncMock()
        mock_client.validate_api_key = AsyncMock(return_value=True)
        mock_create_client.return_value = mock_client
        
        # 테스트 설정
        config = {
            "api_keys": {"claude": "test_key"},
            "api": {"idea_gen_mode": "free"}  # 모드 설정과 관계없이 paid가 우선
        }
        
        # 함수 호출
        client = await create_api_client_by_mode("paid", "idea_gen", config)
        
        # 검증
        mock_create_client.assert_called_once_with("anthropic", config)
        assert client == mock_client


@pytest.mark.asyncio
async def test_create_api_client_by_mode_idea_gen_free():
    """무료 아이디어 생성 API 클라이언트 생성 테스트"""
    # 모듈 및 클래스 모킹
    with patch('src.api.api_client.create_api_client') as mock_create_client:
        # 모킹된 API 클라이언트 설정
        mock_client = AsyncMock()
        mock_client.validate_api_connection = AsyncMock(return_value=True)
        mock_create_client.return_value = mock_client
        
        # 테스트 설정
        config = {
            "api": {"local_ollama_url": "http://localhost:11434"}
        }
        
        # 함수 호출
        client = await create_api_client_by_mode("free", "idea_gen", config)
        
        # 검증
        mock_create_client.assert_called_once_with("ollama", config)
        assert client == mock_client


@pytest.mark.asyncio
async def test_create_api_client_by_mode_code_gen_paid():
    """유료 코드 생성 API 클라이언트 생성 테스트"""
    # 모듈 및 클래스 모킹
    with patch('src.api.api_client.create_api_client') as mock_create_client:
        # 모킹된 API 클라이언트 설정
        mock_client = AsyncMock()
        mock_client.validate_api_key = AsyncMock(return_value=True)
        mock_create_client.return_value = mock_client
        
        # 테스트 설정
        config = {
            "api_keys": {"dalle": "test_key"},  # OpenAI API 키 사용
            "api": {"code_gen_mode": "free"}  # 모드 설정과 관계없이 paid가 우선
        }
        
        # 함수 호출
        client = await create_api_client_by_mode("paid", "code_gen", config)
        
        # 검증
        mock_create_client.assert_called_once_with("openai", config)
        assert client == mock_client


@pytest.mark.asyncio
async def test_create_api_client_by_mode_code_gen_free():
    """무료 코드 생성 API 클라이언트 생성 테스트"""
    # 모듈 및 클래스 모킹
    with patch('src.api.api_client.create_api_client') as mock_create_client:
        # 모킹된 API 클라이언트 설정
        mock_client = AsyncMock()
        mock_client.validate_api_connection = AsyncMock(return_value=True)
        mock_create_client.return_value = mock_client
        
        # 테스트 설정
        config = {
            "api": {"local_ollama_url": "http://localhost:11434"}
        }
        
        # 함수 호출
        client = await create_api_client_by_mode("free", "code_gen", config)
        
        # 검증
        mock_create_client.assert_called_once_with("ollama", config)
        assert client == mock_client


@pytest.mark.asyncio
async def test_create_api_client_by_mode_unknown_type():
    """알 수 없는 API 타입에 대한 처리 테스트"""
    # 테스트 설정
    config = {}
    
    # 함수 호출
    client = await create_api_client_by_mode("free", "unknown_type", config)
    
    # 검증: 기본 BaseAPIClient 반환 확인
    from src.api.api_client import BaseAPIClient
    assert isinstance(client, BaseAPIClient)


@pytest.mark.asyncio
async def test_create_api_client_by_mode_config_override():
    """설정에서 모드 오버라이드 테스트"""
    # 모듈 및 클래스 모킹
    with patch('src.api.api_client.create_api_client') as mock_create_client:
        # 모킹된 API 클라이언트 설정
        mock_client = AsyncMock()
        mock_client.validate_api_key = AsyncMock(return_value=True)
        mock_create_client.return_value = mock_client
        
        # 테스트 설정 - 설정에서 paid 모드 지정
        config = {
            "api_keys": {"dalle": "test_key"},
            "api": {"image_gen_mode": "paid"}
        }
        
        # free 모드로 함수 호출해도 설정의 paid가 우선
        client = await create_api_client_by_mode("free", "image_gen", config)
        
        # 검증 - paid API 클라이언트가 생성되어야 함
        mock_create_client.assert_called_once_with("openai", config)
        assert client == mock_client


@pytest.mark.asyncio
async def test_create_api_client_by_mode_validation_error():
    """API 유효성 검증 오류 처리 테스트"""
    # 모듈 및 클래스 모킹
    with patch('src.api.api_client.create_api_client') as mock_create_client:
        # 모킹된 API 클라이언트 설정
        mock_client = AsyncMock()
        # 유효성 검증 실패 설정
        mock_client.validate_api_key = AsyncMock(side_effect=Exception("유효성 검증 오류"))
        mock_create_client.return_value = mock_client
        
        # 테스트 설정
        config = {
            "api_keys": {"dalle": "test_key"}
        }
        
        # 함수 호출
        client = await create_api_client_by_mode("paid", "image_gen", config)
        
        # 검증 - 오류가 발생해도 클라이언트 반환됨
        assert client == mock_client 