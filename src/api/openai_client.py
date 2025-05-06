"""
OpenAI API 클라이언트

이 모듈은 OpenAI API(텍스트 생성 및 DALL-E 이미지 생성)와 통신하는 기능을 제공합니다.
"""
import logging
import os
import json
from typing import Dict, Any, List, Tuple, Optional
import httpx
import asyncio
import base64
from pathlib import Path

# 내부 모듈 임포트
from src.api.api_client import BaseAPIClient

# 로깅 설정
logger = logging.getLogger(__name__)

class OpenAIClient(BaseAPIClient):
    """OpenAI API 클라이언트 클래스"""
    
    def __init__(self, api_key: str = None):
        """
        OpenAI API 클라이언트 초기화
        
        Args:
            api_key (str, optional): OpenAI API 키
        """
        super().__init__(
            api_key=api_key,
            base_url="https://api.openai.com/v1"
        )
        
        # API 키가 없으면 환경 변수에서 가져오기
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
    
    async def validate_api_key(self) -> bool:
        """
        API 키 유효성 검증
        
        Returns:
            bool: API 키 유효 여부
        """
        # 모델 목록 조회로 API 키 유효성 검증
        success, _ = await self.request(
            method="GET",
            endpoint="/models"
        )
        
        return success
    
    async def generate_text(self, prompt: str, model: str = "gpt-3.5-turbo", 
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
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            success, response = await self.request(
                method="POST",
                endpoint="/chat/completions",
                data=data
            )
            
            if not success:
                return False, response
            
            # 응답에서 텍스트 추출
            generated_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not generated_text:
                return False, {"error": "텍스트 생성에 실패했습니다."}
            
            return True, generated_text
            
        except Exception as e:
            logger.error(f"텍스트 생성 실패: {str(e)}")
            return False, {"error": f"텍스트 생성 중 오류가 발생했습니다: {str(e)}"}
    
    async def generate_image(self, prompt: str, size: str = "1024x1024", 
                            n: int = 1, quality: str = "standard", 
                            output_dir: str = None) -> Tuple[bool, Any]:
        """
        DALL-E 이미지 생성
        
        Args:
            prompt (str): 프롬프트
            size (str, optional): 이미지 크기
            n (int, optional): 생성할 이미지 수
            quality (str, optional): 이미지 품질
            output_dir (str, optional): 이미지 저장 디렉토리
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 이미지 URL 목록 또는 오류 메시지)
        """
        try:
            data = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": n,
                "size": size,
                "quality": quality,
                "response_format": "b64_json" if output_dir else "url"
            }
            
            success, response = await self.request(
                method="POST",
                endpoint="/images/generations",
                data=data
            )
            
            if not success:
                return False, response
            
            # 응답에서 이미지 URL 추출
            results = []
            
            for i, image_data in enumerate(response.get("data", [])):
                if "b64_json" in image_data and output_dir:
                    # 이미지를 파일로 저장
                    output_path = self._save_image(
                        image_data["b64_json"], 
                        output_dir, 
                        f"dalle_{i+1}.png"
                    )
                    results.append({"file_path": output_path})
                elif "url" in image_data:
                    results.append({"url": image_data["url"]})
            
            if not results:
                return False, {"error": "이미지 생성에 실패했습니다."}
            
            return True, results
            
        except Exception as e:
            logger.error(f"이미지 생성 실패: {str(e)}")
            return False, {"error": f"이미지 생성 중 오류가 발생했습니다: {str(e)}"}
    
    def _save_image(self, base64_image: str, output_dir: str, filename: str) -> str:
        """
        Base64 인코딩된 이미지를 파일로 저장
        
        Args:
            base64_image (str): Base64 인코딩된 이미지
            output_dir (str): 출력 디렉토리
            filename (str): 파일 이름
            
        Returns:
            str: 저장된 파일 경로
        """
        # 출력 디렉토리 생성
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 이미지 파일 경로
        file_path = output_path / filename
        
        # Base64 디코딩
        image_data = base64.b64decode(base64_image)
        
        # 파일 저장
        with open(file_path, "wb") as f:
            f.write(image_data)
        
        return str(file_path) 