"""
홈페이지 클론 기획서 생성기 - FastAPI 애플리케이션

이 모듈은 FastAPI 애플리케이션의 메인 진입점입니다.
"""
import logging

# 내부 모듈 임포트
from src.app_config import init_app_config
from src.app_setup import init_app_setup
from src.web_routes import init_web_routes
from src.api_routes import init_api_routes
from src.export_routes import init_export_routes
from src.settings_routes import init_settings_routes
from src.task_routes import init_task_routes

# 로거 설정
logger = logging.getLogger(__name__)

def create_application():
    """애플리케이션 생성 및 초기화"""
    app = init_app_config()  # app을 반환받아 명확히 할당
    init_app_setup(app)
    init_web_routes(app)
    init_api_routes(app)
    init_export_routes(app)
    init_settings_routes(app)
    init_task_routes(app)
    logger.info("애플리케이션 초기화 완료")
    return app

app = create_application()  # uvicorn이 인식할 수 있도록 전역 app에 할당

# 애플리케이션 중복 초기화 방지 (제거)
# if __name__ != "__main__":
#     # 애플리케이션 초기화
#     create_application() 