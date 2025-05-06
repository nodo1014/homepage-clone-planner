"""
설정 관련 엔드포인트

이 모듈은 API 키 설정, 서비스 모드 설정 등 설정 관련 기능을 위한 FastAPI 라우트를 제공합니다.
"""
import os
import logging
from fastapi import Request, Form
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from dotenv import load_dotenv, set_key

# 내부 모듈 임포트
from src.app_config import templates
from src.app_config import base_dir

# .env 파일 경로 설정
DOTENV_PATH = base_dir / ".env"

# 로거 설정
logger = logging.getLogger(__name__)

def register_settings_routes(app):
    """설정 관련 라우트 등록"""
    
    @app.post("/settings/save", tags=["설정"])
    async def save_settings(request: Request):
        """
        API 설정 저장
        
        API 키, 서비스 모드 등 설정 정보를 저장합니다.
        """
        form_data = await request.form()
        
        settings_to_save = {
            "IMAGE_GEN_MODE": form_data.get("image_gen_mode"),
            "OPENAI_API_KEY": form_data.get("openai_api_key"),
            "LOCAL_SD_API_URL": form_data.get("local_sd_url"),
            "IDEA_GEN_MODE": form_data.get("idea_gen_mode"),
            "DEEPSEEK_API_KEY": form_data.get("deepseek_api_key"),
            "LOCAL_OLLAMA_API_URL": form_data.get("local_ollama_url"),
            "OLLAMA_MODEL": form_data.get("ollama_model"),
            "CODE_GEN_MODE": form_data.get("code_gen_mode"),
            "CLAUDE_API_KEY": form_data.get("claude_api_key"),
            "LOCAL_CODE_API_URL": form_data.get("local_code_url"),
        }
        
        try:
            for key, value in settings_to_save.items():
                if value is not None:  # 값이 있는 경우에만 저장 (빈 문자열도 저장)
                    set_key(dotenv_path=DOTENV_PATH, key_to_set=key, value_to_set=value)
            
            # 변경된 환경 변수를 즉시 로드 (선택 사항, 애플리케이션 재시작 없이 적용하려면)
            load_dotenv(override=True) 
            
            # 성공 메시지와 함께 리다이렉트
            return RedirectResponse(url="/settings?message=success", status_code=303)
        except Exception as e:
            logger.error(f"설정 저장 중 오류 발생: {str(e)}")
            # 오류 발생 시 오류 메시지와 함께 리다이렉트
            return RedirectResponse(url=f"/settings?message=error&detail={str(e)}", status_code=303)

    @app.get("/settings", response_class=HTMLResponse, tags=["설정"])
    async def settings_page(request: Request):
        """
        API 설정 페이지
        
        각종 API 설정을 관리하는 페이지를 표시합니다.
        """
        # 매번 최신 .env 파일 내용 로드
        load_dotenv(override=True) 
        
        api_settings = {
            "image_gen_mode": os.getenv("IMAGE_GEN_MODE", "free"),
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""), # 키는 기본값을 빈 문자열로
            "local_sd_url": os.getenv("LOCAL_SD_API_URL", "http://localhost:7860/sdapi/v1"),
            "idea_gen_mode": os.getenv("IDEA_GEN_MODE", "free"),
            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "local_ollama_url": os.getenv("LOCAL_OLLAMA_API_URL", "http://localhost:11434/api"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "mistral"),
            "code_gen_mode": os.getenv("CODE_GEN_MODE", "free"),
            "claude_api_key": os.getenv("CLAUDE_API_KEY", ""),
            "local_code_url": os.getenv("LOCAL_CODE_API_URL", "http://localhost:8080/v1"),
        }
        
        message = request.query_params.get("message")
        detail = request.query_params.get("detail")
        
        return templates.TemplateResponse(
            "settings.html", 
            {
                "request": request, 
                "title": "API 설정", 
                "settings": api_settings,
                "message": message,
                "detail": detail
            }
        )

    @app.get("/settings/test/{api_type}", tags=["설정"])
    async def test_api(request: Request, api_type: str):
        """
        API 키 유효성 테스트
        
        - **api_type**: 테스트할 API 타입 (openai, deepseek, claude 등)
        
        설정된 API 키가 유효한지 테스트합니다.
        """
        # API 유효성 테스트 로직 구현
        try:
            if api_type == "openai":
                import openai
                api_key = os.getenv("OPENAI_API_KEY", "")
                if not api_key:
                    return JSONResponse(
                        status_code=400,
                        content={"status": "error", "message": "OpenAI API 키가 설정되지 않았습니다."}
                    )
                
                # OpenAI API 테스트
                openai.api_key = api_key
                models = openai.models.list()
                return JSONResponse(
                    content={"status": "success", "message": "OpenAI API 연결에 성공했습니다."}
                )
                
            elif api_type == "deepseek":
                api_key = os.getenv("DEEPSEEK_API_KEY", "")
                if not api_key:
                    return JSONResponse(
                        status_code=400,
                        content={"status": "error", "message": "Deepseek API 키가 설정되지 않았습니다."}
                    )
                
                # Deepseek API 테스트는 실제 구현 필요 (여기서는 간단히 키 존재 여부만 확인)
                return JSONResponse(
                    content={"status": "success", "message": "Deepseek API 키가 설정되어 있습니다. 실제 연결 테스트가 필요합니다."}
                )
                
            elif api_type == "claude":
                api_key = os.getenv("CLAUDE_API_KEY", "")
                if not api_key:
                    return JSONResponse(
                        status_code=400,
                        content={"status": "error", "message": "Claude API 키가 설정되지 않았습니다."}
                    )
                
                # Anthropic Claude API 테스트는 실제 구현 필요 (여기서는 간단히 키 존재 여부만 확인)
                return JSONResponse(
                    content={"status": "success", "message": "Claude API 키가 설정되어 있습니다. 실제 연결 테스트가 필요합니다."}
                )
                
            elif api_type == "local_sd":
                import requests
                url = os.getenv("LOCAL_SD_API_URL", "http://localhost:7860/sdapi/v1")
                if not url:
                    return JSONResponse(
                        status_code=400,
                        content={"status": "error", "message": "Stable Diffusion API URL이 설정되지 않았습니다."}
                    )
                
                # Stable Diffusion API 연결 테스트
                response = requests.get(f"{url}/options", timeout=5)
                if response.status_code == 200:
                    return JSONResponse(
                        content={"status": "success", "message": "Stable Diffusion API 연결에 성공했습니다."}
                    )
                else:
                    return JSONResponse(
                        status_code=400,
                        content={"status": "error", "message": f"Stable Diffusion API 연결에 실패했습니다: {response.status_code}"}
                    )
                    
            elif api_type == "local_ollama":
                import requests
                url = os.getenv("LOCAL_OLLAMA_API_URL", "http://localhost:11434/api")
                if not url:
                    return JSONResponse(
                        status_code=400,
                        content={"status": "error", "message": "Ollama API URL이 설정되지 않았습니다."}
                    )
                
                # Ollama API 연결 테스트
                response = requests.get(f"{url}/tags", timeout=5)
                if response.status_code == 200:
                    return JSONResponse(
                        content={"status": "success", "message": "Ollama API 연결에 성공했습니다."}
                    )
                else:
                    return JSONResponse(
                        status_code=400,
                        content={"status": "error", "message": f"Ollama API 연결에 실패했습니다: {response.status_code}"}
                    )
                    
            else:
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "message": f"지원하지 않는 API 유형: {api_type}"}
                )
                
        except Exception as e:
            logger.error(f"API 테스트 중 오류 발생: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"API 테스트 중 오류가 발생했습니다: {str(e)}"}
            )

def init_settings_routes(app):
    """설정 라우트 초기화"""
    register_settings_routes(app)
    logger.info("설정 라우트 초기화 완료") 