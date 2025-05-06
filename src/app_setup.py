"""
애플리케이션 이벤트 핸들러 설정

이 모듈은 FastAPI 애플리케이션의 시작/종료 시 실행되는
이벤트 핸들러와 관련 기능을 제공합니다.
"""
import logging
from src.utils.cleaner import clean_database

# 로거 설정
logger = logging.getLogger(__name__)

async def startup_event_handler():
    """애플리케이션 시작 시 필요한 초기화 작업 수행"""
    logger.info("애플리케이션 시작")
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest
    # app 인스턴스는 클로저로 접근 (FastAPI의 글로벌 app import 또는 app.state 활용)
    import src.app_config as app_config
    app = app_config.app
    scheduler = app.state.scheduler
    outputs_dir = app.state.outputs_dir
    scheduler.add_job(
        lambda: clean_database(outputs_dir),
        'interval',
        hours=24,
        id="clean_database",
        replace_existing=True
    )
    # 스케줄러가 이미 실행 중인지 확인
    if not scheduler.running:
        scheduler.start()
        logger.info("스케줄러 시작 완료")
    else:
        logger.info("스케줄러는 이미 실행 중입니다.")

async def shutdown_event_handler():
    """애플리케이션 종료 시 필요한 정리 작업 수행"""
    logger.info("애플리케이션 종료")
    import src.app_config as app_config
    app = app_config.app
    scheduler = app.state.scheduler
    if scheduler.running:
        scheduler.shutdown()
        logger.info("스케줄러 종료 완료")

def init_app_setup(app_instance):
    """애플리케이션 이벤트 핸들러 설정"""
    app_instance.add_event_handler("startup", startup_event_handler)
    app_instance.add_event_handler("shutdown", shutdown_event_handler)
    logger.info("애플리케이션 이벤트 핸들러 설정 완료")
    return app_instance 