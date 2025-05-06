"""
애플리케이션 설정 및 초기화 관련 코드

이 모듈은 FastAPI 애플리케이션의 설정, 로깅, 디렉토리 구성, 
데이터베이스 연결 등 초기화 관련 기능을 제공합니다.
"""
import os
import logging
import logging.handlers
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv, set_key
import shutil
from datetime import datetime
import time
from fastapi.responses import JSONResponse
from src.utils.bug_reporter import log_bug

# API 키 관리 문제 해결을 위한 fallback 설정
try:
    # keyring 패키지 로드 시도
    import keyring
    # 백엔드가 없으면 keyrings.alt를 시도
    if not keyring.get_keyring():
        try:
            import keyrings.alt
            logger = logging.getLogger(__name__)
            logger.info("keyrings.alt 사용 중")
        except ImportError:
            logger = logging.getLogger(__name__)
            logger.warning("keyrings.alt 패키지가 설치되어 있지 않습니다. API 키 저장에 문제가 발생할 수 있습니다.")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("keyring 패키지가 설치되어 있지 않습니다. API 키 저장에 문제가 발생할 수 있습니다.")

# 내부 모듈 임포트
from src.utils.config import load_config
from src.utils import task_manager
from src.database.migrations.migration_manager import MigrationManager
from src.database.db_manager import DBManager
from src.app_setup import init_app_setup
from src.utils.cleaner import clean_database

# 전역 변수
app = None
scheduler = None
templates = None  # 전역 템플릿 객체
db_manager = None
migration_manager = None
base_dir = Path(__file__).resolve().parent.parent
templates_dir = base_dir / "src" / "templates"
static_dir = base_dir / "src" / "static"
outputs_dir = base_dir / "outputs"
database_dir = base_dir / "database"
exports_dir = base_dir / "exports"
logs_dir = base_dir / "logs"
docs_dir = base_dir / "docs"

# 상수 변수 추가 (대문자 이름 규칙)
RESULTS_DIR = outputs_dir
EXPORTS_DIR = exports_dir
DOTENV_PATH = base_dir / ".env"
EMAIL_TEMPLATE_PATH = templates_dir / "email" / "results.html"

# API 문서 디렉토리 (docs_dir과 동일, 변수명 통일)
DOCS_DIR = docs_dir

# 환경 변수 초기화
def init_env():
    """환경 변수 초기화"""
    # .env 파일 로드
    env_path = base_dir / ".env"
    load_dotenv(dotenv_path=env_path)
    
    # .env 파일이 없으면 기본 설정으로 생성
    if not env_path.exists():
        with open(env_path, "w") as f:
            f.write("# 환경 변수 설정\n")
            f.write("DEBUG=True\n")
            f.write("API_MODE=free\n")
        load_dotenv(dotenv_path=env_path)

# 디렉토리 초기화
def init_directories():
    """필요한 디렉토리 초기화"""
    for directory in [
        database_dir, outputs_dir, exports_dir, logs_dir, docs_dir,
        outputs_dir / "ai_analysis"  # AI 분석 결과 저장 디렉토리
    ]:
        directory.mkdir(exist_ok=True)

# 로깅 초기화
def init_logging():
    """로깅 시스템 초기화"""
    log_file = logs_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 (로그 파일에 저장)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러 (터미널에 출력)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 써드파티 로거 레벨 조정
    logging.getLogger('httpx').setLevel(logging.INFO)
    logging.getLogger('apscheduler').setLevel(logging.INFO)
    
    root_logger.info("로깅 시스템 초기화 완료")

# FastAPI 애플리케이션 초기화
def init_app():
    """FastAPI 애플리케이션 초기화"""
    global app, templates, scheduler
    
    # FastAPI 앱 생성
    app = FastAPI(title="홈페이지 클론 기획서 생성기")
    
    # 스케줄러 생성
    scheduler = AsyncIOScheduler()
    app.state.scheduler = scheduler # FastAPI app 상태에 스케줄러 저장
    app.state.outputs_dir = outputs_dir # outputs_dir도 app.state에 저장
    
    # 글로벌 예외 핸들러 등록
    add_global_exception_handler(app)
    
    # 템플릿 엔진 설정 - 전역 변수 templates에 할당하고 app.state에도 저장
    templates = Jinja2Templates(directory=templates_dir)
    app.state.templates = templates  # app.state에도 저장하여 어디서든 접근 가능하게 함
    app.templates = templates
    
    # 정적 파일 마운트
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")
    app.mount("/exports", StaticFiles(directory=exports_dir), name="exports")

# 데이터베이스 초기화
def init_database():
    """데이터베이스 초기화"""
    global db_manager, migration_manager
    
    # 데이터베이스 경로
    db_path = database_dir / "database.db"
    
    # 데이터베이스 관리자 생성
    db_manager = DBManager(db_path)
    
    # 마이그레이션 관리자 생성 (비활성화된 상태)
    migrations_dir = base_dir / "src" / "database" / "migrations"
    migration_manager = MigrationManager(str(db_path), str(migrations_dir))
    
    # 스키마 변경 체크 및 마이그레이션 적용은 비활성화
    # 마이그레이션 관련 코드가 app_setup.py에서 제거됨

# 작업 관리자 초기화
def init_task_manager():
    """작업 관리자 초기화"""
    task_manager.init_manager(str(outputs_dir))

# 애플리케이션 초기화 함수
def init_app_config():
    """애플리케이션 설정 초기화"""
    # 환경 변수 및 디렉토리 초기화
    init_env()
    init_directories()
    init_logging()
    
    # FastAPI 앱 초기화
    init_app()
    
    # 데이터베이스 및 작업 관리자 초기화
    init_database()
    init_task_manager()
    
    # 설정 로드
    load_config()

    # 이벤트 핸들러 설정
    init_app_setup(app)
    
    return app 

def add_global_exception_handler(app):
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log_bug(exc, {"url": str(request.url)})
        return JSONResponse(
            status_code=500,
            content={"detail": "서버 내부 오류가 발생했습니다. 관리자에게 문의하세요."}
        ) 