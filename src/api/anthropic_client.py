"""
Anthropic Claude API 클라이언트

이 모듈은 Anthropic Claude API와 통신하는 기능을 제공합니다.
"""
import logging
import os
import json
from typing import Dict, Any, List, Tuple, Optional
import httpx
import asyncio
from pathlib import Path

# 내부 모듈 임포트
from src.api.api_client import BaseAPIClient

# 로깅 설정
logger = logging.getLogger(__name__)

class ClaudeClient(BaseAPIClient):
    """Anthropic Claude API 클라이언트 클래스"""
    
    def __init__(self, api_key: str = None):
        """
        Claude API 클라이언트 초기화
        
        Args:
            api_key (str, optional): Claude API 키
        """
        super().__init__(
            api_key=api_key,
            base_url="https://api.anthropic.com/v1"
        )
        
        # API 키가 없으면 환경 변수에서 가져오기
        if not self.api_key:
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
    
    async def validate_api_key(self) -> bool:
        """
        API 키 유효성 검증
        
        Returns:
            bool: API 키 유효 여부
        """
        # Claude API는 별도의 검증 엔드포인트가 없어 짧은 메시지 생성으로 테스트
        success, _ = await self.generate_text("API 키 유효성 검증", max_tokens=10)
        return success
    
    async def generate_text(self, prompt: str, model: str = "claude-3-opus-20240229", 
                           max_tokens: int = 500) -> Tuple[bool, Any]:
        """
        텍스트 생성
        
        Args:
            prompt (str): 프롬프트
            model (str, optional): 모델 이름
            max_tokens (int, optional): 최대 토큰 수
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 생성된 텍스트 또는 오류 메시지)
        """
        try:
            data = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            # Claude API는 Authorization 헤더 형식이 다름
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            success, response = await self.request(
                method="POST",
                endpoint="/messages",
                data=data,
                headers=headers
            )
            
            if not success:
                return False, response
            
            # 응답에서 텍스트 추출
            content = response.get("content", [])
            text = ""
            
            for item in content:
                if item.get("type") == "text":
                    text += item.get("text", "")
            
            if not text:
                return False, {"error": "텍스트 생성에 실패했습니다."}
            
            return True, text
            
        except Exception as e:
            logger.error(f"텍스트 생성 실패: {str(e)}")
            return False, {"error": f"텍스트 생성 중 오류가 발생했습니다: {str(e)}"}
    
    async def request(self, method: str, endpoint: str, data: Dict[str, Any] = None, 
                     params: Dict[str, Any] = None, headers: Dict[str, Any] = None) -> Tuple[bool, Any]:
        """
        API 요청 전송 (오버라이드)
        
        Claude API는 인증 방식이 다르므로 부모 클래스의 메소드를 오버라이드
        
        Args:
            method (str): HTTP 메서드 (GET, POST 등)
            endpoint (str): API 엔드포인트
            data (Dict[str, Any], optional): 요청 본문 데이터
            params (Dict[str, Any], optional): URL 쿼리 파라미터
            headers (Dict[str, Any], optional): HTTP 헤더
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 응답 데이터 또는 오류 메시지)
        """
        if headers is None:
            headers = {}
            
        # Claude API 특화 헤더 설정
        if self.api_key and "x-api-key" not in headers:
            headers["x-api-key"] = self.api_key
            
        if "anthropic-version" not in headers:
            headers["anthropic-version"] = "2023-06-01"
            
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        
        url = f"{self.base_url}{endpoint}" if self.base_url else endpoint
        
        try:
            response = await self.client.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers
            )
            
            # 응답 검사
            response.raise_for_status()
            
            # JSON 응답인 경우 파싱
            if "application/json" in response.headers.get("Content-Type", ""):
                return True, response.json()
            
            # 그 외의 경우 텍스트 반환
            return True, response.text
        
        except httpx.HTTPStatusError as e:
            logger.error(f"API 요청 실패 (HTTP {e.response.status_code}): {str(e)}")
            
            # 오류 응답이 JSON인 경우 파싱
            try:
                error_data = e.response.json()
                return False, error_data
            except:
                return False, {"error": f"API 요청 실패: HTTP {e.response.status_code}", "details": str(e)}
        
        except httpx.RequestError as e:
            logger.error(f"API 요청 실패 (네트워크 오류): {str(e)}")
            return False, {"error": "네트워크 오류", "details": str(e)}
        
        except Exception as e:
            logger.error(f"API 요청 중 오류 발생: {str(e)}")
            return False, {"error": "API 요청 중 오류 발생", "details": str(e)} 