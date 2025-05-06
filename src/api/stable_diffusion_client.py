"""
Stable Diffusion API 클라이언트

이 모듈은 로컬 Stable Diffusion 웹 UI API와 통신하는 기능을 제공합니다.
"""
import logging
import os
import json
import base64
from typing import Dict, Any, List, Tuple, Optional
import httpx
import asyncio
from pathlib import Path

# 내부 모듈 임포트
from src.api.api_client import BaseAPIClient

# 로깅 설정
logger = logging.getLogger(__name__)

class StableDiffusionClient(BaseAPIClient):
    """Stable Diffusion API 클라이언트 클래스"""
    
    def __init__(self, api_url: str = None):
        """
        Stable Diffusion API 클라이언트 초기화
        
        Args:
            api_url (str, optional): API URL
        """
        # API URL이 없으면 환경 변수에서 가져오기
        api_url = api_url or os.getenv("LOCAL_SD_API_URL", "http://localhost:7860/sdapi/v1")
        
        super().__init__(
            api_key=None,  # 로컬 API는 API 키 불필요
            base_url=api_url
        )
        
        # 기본 모델 설정
        self.model_name = os.getenv("SD_MODEL_NAME", "v1-5-pruned-emaonly")
    
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
                endpoint="/sd-models"
            )
            
            return success
        except Exception as e:
            logger.error(f"API 연결 유효성 검증 실패: {str(e)}")
            return False
    
    async def generate_image(self, prompt: str, negative_prompt: str = "", 
                            width: int = 512, height: int = 512, 
                            steps: int = 20, guidance_scale: float = 7.5,
                            seed: int = -1, output_dir: str = None) -> Tuple[bool, Any]:
        """
        이미지 생성
        
        Args:
            prompt (str): 프롬프트
            negative_prompt (str, optional): 네거티브 프롬프트
            width (int, optional): 이미지 너비
            height (int, optional): 이미지 높이
            steps (int, optional): 생성 스텝 수
            guidance_scale (float, optional): CFG 스케일
            seed (int, optional): 시드 값 (-1은 랜덤)
            output_dir (str, optional): 이미지 저장 디렉토리
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 이미지 파일 경로 또는 오류 메시지)
        """
        try:
            # 현재 모델 확인 및 설정
            await self._ensure_model_loaded()
            
            # 이미지 생성 요청 데이터
            data = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": guidance_scale,
                "seed": seed,
                "sampler_name": "Euler a",
                "batch_size": 1
            }
            
            success, response = await self.request(
                method="POST",
                endpoint="/txt2img",
                data=data
            )
            
            if not success:
                return False, response
            
            # 응답에서 이미지 추출
            if "images" not in response or not response["images"]:
                return False, {"error": "이미지 생성에 실패했습니다."}
            
            base64_image = response["images"][0]
            
            # 이미지를 파일로 저장 (지정된 경우)
            if output_dir:
                # 현재 시간을 파일명에 포함
                import time
                timestamp = int(time.time())
                filename = f"sd_{timestamp}.png"
                
                file_path = self._save_image(base64_image, output_dir, filename)
                return True, {"file_path": file_path}
            
            # 그렇지 않으면 Base64 이미지 반환
            return True, {"base64_image": base64_image}
            
        except Exception as e:
            logger.error(f"이미지 생성 실패: {str(e)}")
            return False, {"error": f"이미지 생성 중 오류가 발생했습니다: {str(e)}"}
    
    async def _ensure_model_loaded(self) -> bool:
        """
        지정된 모델이 로드되었는지 확인하고, 로드되지 않았으면 로드
        
        Returns:
            bool: 모델 로드 성공 여부
        """
        try:
            # 현재 옵션 조회
            success, options = await self.request(
                method="GET",
                endpoint="/options"
            )
            
            if not success:
                return False
            
            # 현재 모델이 지정된 모델과 다르면 모델 변경
            current_model = options.get("sd_model_checkpoint", "")
            if current_model != self.model_name:
                await self.request(
                    method="POST",
                    endpoint="/options",
                    data={"sd_model_checkpoint": self.model_name}
                )
            
            return True
        except Exception as e:
            logger.error(f"모델 로드 확인 실패: {str(e)}")
            return False
    
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