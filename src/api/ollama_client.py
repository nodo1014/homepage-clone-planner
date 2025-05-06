"""
Ollama API 클라이언트

이 모듈은 로컬 Ollama API와 통신하는 기능을 제공합니다.
"""
import logging
import os
import json
from typing import Dict, Any, List, Tuple, Optional
import httpx
import asyncio

# 내부 모듈 임포트
from src.api.api_client import BaseAPIClient

# 로깅 설정
logger = logging.getLogger(__name__)

class OllamaClient(BaseAPIClient):
    """Ollama API 클라이언트 클래스"""
    
    def __init__(self, api_url: str = None):
        """
        Ollama API 클라이언트 초기화
        
        Args:
            api_url (str, optional): API URL
        """
        # API URL이 없으면 환경 변수에서 가져오기
        api_url = api_url or os.getenv("LOCAL_OLLAMA_API_URL", "http://localhost:11434/api")
        
        super().__init__(
            api_key=None,  # 로컬 API는 API 키 불필요
            base_url=api_url
        )
        
        # 기본 모델 설정
        self.model_name = os.getenv("OLLAMA_MODEL_NAME", "mistral")
    
    async def validate_api_connection(self) -> bool:
        """
        API 연결 유효성 검증
        
        Returns:
            bool: 연결 유효 여부
        """
        try:
            # 모델 목록 조회로 연결 유효성 검증
            success, _ = await self.request(
                method="GET",
                endpoint="/tags"
            )
            
            return success
        except Exception as e:
            logger.error(f"API 연결 유효성 검증 실패: {str(e)}")
            return False
    
    async def generate_text(self, prompt: str, model: str = None, 
                           max_tokens: int = 500, temperature: float = 0.7) -> Tuple[bool, Any]:
        """
        텍스트 생성
        
        Args:
            prompt (str): 프롬프트
            model (str, optional): 모델 이름 (지정하지 않으면 기본 모델 사용)
            max_tokens (int, optional): 최대 토큰 수
            temperature (float, optional): 온도 값 (높을수록 창의적, 낮을수록 결정적)
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 생성된 텍스트 또는 오류 메시지)
        """
        try:
            # 모델 이름이 지정되지 않았으면 기본 모델 사용
            model = model or self.model_name
            
            # 요청 데이터
            data = {
                "model": model,
                "prompt": prompt,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                },
                "stream": False
            }
            
            success, response = await self.request(
                method="POST",
                endpoint="/generate",
                data=data
            )
            
            if not success:
                return False, response
            
            # 응답에서 텍스트 추출
            generated_text = response.get("response", "")
            
            if not generated_text:
                return False, {"error": "텍스트 생성에 실패했습니다."}
            
            return True, generated_text
            
        except Exception as e:
            logger.error(f"텍스트 생성 실패: {str(e)}")
            return False, {"error": f"텍스트 생성 중 오류가 발생했습니다: {str(e)}"}
    
    async def list_models(self) -> Tuple[bool, Any]:
        """
        사용 가능한 모델 목록 조회
        
        Returns:
            Tuple[bool, Any]: (성공 여부, 모델 목록 또는 오류 메시지)
        """
        try:
            success, response = await self.request(
                method="GET",
                endpoint="/tags"
            )
            
            if not success:
                return False, response
            
            # 응답에서 모델 목록 추출
            models = response.get("models", [])
            
            # 간소화된 모델 정보 반환
            simplified_models = []
            for model in models:
                simplified_models.append({
                    "name": model.get("name", ""),
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", "")
                })
            
            return True, simplified_models
            
        except Exception as e:
            logger.error(f"모델 목록 조회 실패: {str(e)}")
            return False, {"error": f"모델 목록 조회 중 오류가 발생했습니다: {str(e)}"}
    
    async def chat_completion(self, messages: List[Dict[str, str]], model: str = None,
                             max_tokens: int = 500, temperature: float = 0.7) -> Tuple[bool, Any]:
        """
        채팅 완성
        
        Args:
            messages (List[Dict[str, str]]): 메시지 목록 
                (예: [{"role": "user", "content": "안녕하세요"}])
            model (str, optional): 모델 이름 (지정하지 않으면 기본 모델 사용)
            max_tokens (int, optional): 최대 토큰 수
            temperature (float, optional): 온도 값
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 생성된 응답 또는 오류 메시지)
        """
        try:
            # 모델 이름이 지정되지 않았으면 기본 모델 사용
            model = model or self.model_name
            
            # 요청 데이터
            data = {
                "model": model,
                "messages": messages,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                },
                "stream": False
            }
            
            success, response = await self.request(
                method="POST",
                endpoint="/chat",
                data=data
            )
            
            if not success:
                return False, response
            
            # 응답에서 메시지 추출
            message = response.get("message", {})
            content = message.get("content", "")
            
            if not content:
                return False, {"error": "응답 생성에 실패했습니다."}
            
            return True, content
            
        except Exception as e:
            logger.error(f"채팅 완성 실패: {str(e)}")
            return False, {"error": f"채팅 완성 중 오류가 발생했습니다: {str(e)}"}
    
    async def create_embedding(self, text: str, model: str = None) -> Tuple[bool, Any]:
        """
        텍스트 임베딩 생성
        
        Args:
            text (str): 임베딩을 생성할 텍스트
            model (str, optional): 모델 이름 (지정하지 않으면 기본 모델 사용)
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 임베딩 또는 오류 메시지)
        """
        try:
            # 모델 이름이 지정되지 않았으면 기본 모델 사용
            model = model or self.model_name
            
            # 요청 데이터
            data = {
                "model": model,
                "prompt": text
            }
            
            success, response = await self.request(
                method="POST",
                endpoint="/embeddings",
                data=data
            )
            
            if not success:
                return False, response
            
            # 응답에서 임베딩 추출
            embedding = response.get("embedding", [])
            
            if not embedding:
                return False, {"error": "임베딩 생성에 실패했습니다."}
            
            return True, embedding
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {str(e)}")
            return False, {"error": f"임베딩 생성 중 오류가 발생했습니다: {str(e)}"} 