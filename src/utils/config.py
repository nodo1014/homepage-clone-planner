"""
환경 설정 로드 및 관리

이 모듈은 애플리케이션 환경 설정을 로드하고 관리하는 기능을 제공합니다.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import keyring
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """
    환경 설정 로드
    
    .env 파일과 시스템 키체인에서 설정을 로드합니다.
    
    Returns:
        Dict[str, Any]: 설정 정보를 담고 있는 딕셔너리
    """
    # 환경 변수 로드
    load_dotenv()
    
    # 기본 설정
    config = {
        "api": {
            "image_gen_mode": os.getenv("IMAGE_GEN_MODE", "free"),
            "idea_gen_mode": os.getenv("IDEA_GEN_MODE", "free"),
            "code_gen_mode": os.getenv("CODE_GEN_MODE", "free"),
            "local_sd_url": os.getenv("LOCAL_SD_API_URL", "http://localhost:7860/sdapi/v1"),
            "local_ollama_url": os.getenv("LOCAL_OLLAMA_API_URL", "http://localhost:11434/api"),
            "local_code_url": os.getenv("LOCAL_CODE_API_URL", "http://localhost:8080/v1"),
            "sd_model_name": os.getenv("SD_MODEL_NAME", "v1-5-pruned-emaonly"),
            "ollama_model_name": os.getenv("OLLAMA_MODEL_NAME", "mistral"),
            "localai_model_name": os.getenv("LOCALAI_MODEL_NAME", "ggml-gpt4all-j"),
        },
        "app": {
            "output_dir": os.getenv("OUTPUT_DIR", "./output"),
            "analysis_timeout": int(os.getenv("ANALYSIS_TIMEOUT", "20")),
            "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        }
    }
    
    # API 키 로드
    config["api_keys"] = load_api_keys()
    
    return config

def load_api_keys() -> Dict[str, Optional[str]]:
    """
    시스템 키체인에서 API 키 로드
    
    Returns:
        Dict[str, Optional[str]]: API 키 정보
    """
    api_keys = {}
    
    for api_name in ["dalle", "deepseek", "claude"]:
        try:
            api_keys[api_name] = keyring.get_password("cloner", f"{api_name}_api_key")
        except Exception as e:
            logger.warning(f"API 키 로드 실패 ({api_name}): {str(e)}")
            api_keys[api_name] = None
    
    return api_keys

def save_api_key(api_name: str, api_key: str) -> bool:
    """
    API 키를 시스템 키체인에 저장
    
    Args:
        api_name (str): API 서비스 이름 (dalle, deepseek, claude)
        api_key (str): API 키 값
        
    Returns:
        bool: 저장 성공 여부
    """
    if not api_key:
        return False
        
    try:
        keyring.set_password("cloner", f"{api_name}_api_key", api_key)
        return True
    except Exception as e:
        logger.error(f"API 키 저장 실패 ({api_name}): {str(e)}")
        return False

def update_env_setting(key: str, value: str) -> bool:
    """
    .env 파일의 설정 업데이트
    
    Args:
        key (str): 환경 변수 키
        value (str): 환경 변수 값
        
    Returns:
        bool: 업데이트 성공 여부
    """
    try:
        dotenv_file = Path(".env")
        
        if dotenv_file.exists():
            # 파일 읽기
            with open(dotenv_file, 'r') as f:
                lines = f.readlines()
            
            # 파일 업데이트
            updated = False
            with open(dotenv_file, 'w') as f:
                for line in lines:
                    if line.startswith(f"{key}="):
                        f.write(f"{key}={value}\n")
                        updated = True
                    else:
                        f.write(line)
                
                # 키가 없으면 새로 추가
                if not updated:
                    f.write(f"{key}={value}\n")
        else:
            # 파일이 없으면 새로 생성
            with open(dotenv_file, 'w') as f:
                f.write(f"{key}={value}\n")
        
        # 환경 변수 업데이트
        os.environ[key] = value
        return True
    except Exception as e:
        logger.error(f"환경 설정 업데이트 실패 ({key}): {str(e)}")
        return False

def get_api_usage() -> Dict[str, Any]:
    """
    API 사용량 조회
    
    각 API 서비스의 사용량을 조회합니다.
    
    Returns:
        Dict[str, Any]: API 사용량 정보
    """
    # 기본 정보로 설정 (실제로는 각 API 제공자에게 요청해야 함)
    usage = {
        "dalle": {
            "used": 0,
            "limit": 0,
            "available": True
        },
        "deepseek": {
            "used": 0,
            "limit": 0,
            "available": True
        },
        "claude": {
            "used": 0,
            "limit": 0,
            "available": True
        }
    }
    
    # 실제 구현에서는 각 API 제공자에게 사용량 조회 요청
    # TODO: 실제 API 사용량 조회 구현
    
    return usage 