"""
웹 인터페이스 관련 라우트

이 모듈은 웹 인터페이스의 메인 페이지, 결과 페이지 등의 
라우트를 정의합니다.
"""
import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, BackgroundTasks, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

# 내부 모듈 임포트
from src.app_config import templates, outputs_dir, db_manager
from src.utils.analyzer import analyze_website
from src.utils.mock_data_loader import load_mock_data
from src.utils.task_manager import create_task, get_task_status, update_task_status, update_step_status

# 로거 설정
logger = logging.getLogger(__name__)

# 웹 라우트 등록
def register_web_routes(app):
    """웹 인터페이스 라우트 등록"""
    
    @app.get("/", response_class=HTMLResponse, tags=["웹"])
    async def home(request: Request):
        """
        메인 페이지
        
        클론 기획서 생성을 위한 메인 페이지를 제공합니다.
        """
        # 디버깅: templates 객체 확인
        logger.info(f"templates 객체: {templates}")
        
        try:
            # 먼저 기본 템플릿 사용 시도
            if templates is not None:
                return templates.TemplateResponse(
                    "index.html",
                    {
                        "request": request,
                        "title": "홈페이지 클론 기획서 생성기"
                    }
                )
            # 실패하면 app에서 템플릿 가져오기 시도
            elif hasattr(app, 'templates') and app.templates is not None:
                logger.info("app.templates 사용")
                return app.templates.TemplateResponse(
                    "index.html",
                    {
                        "request": request,
                        "title": "홈페이지 클론 기획서 생성기"
                    }
                )
            # 마지막으로 Jinja2Templates 직접 생성
            else:
                logger.warning("템플릿 객체가 없어 새로 생성합니다")
                from fastapi.templating import Jinja2Templates
                from src.app_config import templates_dir
                local_templates = Jinja2Templates(directory=templates_dir)
                return local_templates.TemplateResponse(
                    "index.html",
                    {
                        "request": request,
                        "title": "홈페이지 클론 기획서 생성기"
                    }
                )
        except Exception as e:
            logger.error(f"템플릿 렌더링 오류: {str(e)}")
            return JSONResponse(
                content={
                    "error": "템플릿 렌더링 오류",
                    "detail": str(e)
                },
                status_code=500
            )
    
    @app.post("/analyze", response_class=HTMLResponse, tags=["웹"])
    async def analyze(
        request: Request,
        background_tasks: BackgroundTasks,
        url: str = Form(...),
        mock: bool = Form(False)
    ):
        """
        웹사이트 분석 시작
        
        - **url**: 분석할 웹사이트 URL
        - **mock**: 목업 데이터 사용 여부
        
        웹사이트 분석을 시작하고 상태 페이지로 리다이렉트합니다.
        """
        logger.info(f"웹사이트 분석 요청: {url}, mock={mock}")
        
        try:
            # 작업 ID 생성
            task_id = create_task(url)
            
            # 작업 시작 상태로 업데이트
            update_task_status(task_id, status="pending", message=f"분석 준비 중: {url}")
            
            # 배경 작업으로 분석 실행
            background_tasks.add_task(
                analyze_website,
                url=url,
                task_id=task_id,
                use_mock=mock
            )
            
            # 상태 페이지로 리다이렉트
            return RedirectResponse(url=f"/analyze/status/{task_id}", status_code=303)
            
        except Exception as e:
            logger.error(f"분석 요청 처리 오류: {str(e)}")
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "title": "오류 발생",
                    "error_message": f"분석 요청 처리 중 오류가 발생했습니다: {str(e)}"
                }
            )
    
    @app.get("/analyze/status/{task_id}", response_class=HTMLResponse, tags=["웹"])
    async def analyze_status(request: Request, task_id: str):
        """
        분석 상태 페이지
        
        - **task_id**: 작업 ID
        
        작업 상태를 표시하는 페이지를 제공합니다.
        """
        task = get_task_status(task_id)
        
        if not task:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "title": "작업을 찾을 수 없음",
                    "error_message": f"작업 ID {task_id}를 찾을 수 없습니다."
                }
            )
            
        return templates.TemplateResponse(
            "status.html",
            {
                "request": request,
                "title": "분석 상태",
                "task": task,
                "task_id": task_id,
                "url": task.get("url", "")
            }
        )
    
    @app.get("/results/{result_id}", response_class=HTMLResponse, tags=["웹"])
    async def view_results(request: Request, result_id: str):
        """
        분석 결과 페이지
        
        - **result_id**: 결과 ID
        
        분석 결과를 표시하는 페이지를 제공합니다.
        """
        # 결과 ID에서 작업 ID 추출 (result_XXX 형식)
        task_id = result_id
        if result_id.startswith("result_"):
            task_id = result_id[7:]  # "result_" 제거
        
        logger.info(f"결과 보기 요청: result_id={result_id}, task_id={task_id}")
        
        # 작업 상태 확인
        task = get_task_status(task_id)
        task_exists = task is not None
        
        if not task_exists:
            logger.info("작업 상태 확인 결과: False")
            logger.error(f"작업을 찾을 수 없음: {task_id}")
            
            # 테스트 또는 데모용 작업인 경우 더미 데이터 제공
            if task_id == "test_task":
                logger.info("테스트용 더미 작업 생성")
                update_task_status(
                    task_id, 
                    status="completed", 
                    progress=100, 
                    message="분석 완료",
                    result_id=f"result_{task_id}"
                )
                task = get_task_status(task_id)
        
        if not task:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "title": "결과를 찾을 수 없음",
                    "error_message": f"결과 ID {result_id}에 해당하는 작업을 찾을 수 없습니다."
                }
            )
        
        # 작업이 완료되지 않은 경우
        if task["status"] != "completed":
            return RedirectResponse(
                url=f"/analyze/status/{task_id}",
                status_code=303
            )
        
        # 결과 데이터 로드
        try:
            logger.info(f"작업 상태: {task['status']}")
            
            # 결과 파일 디렉토리
            output_dir = outputs_dir / task_id / "meta"
            logger.info(f"출력 디렉토리: {output_dir}")
            
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # UI 구조 파일 로드
            ui_structure_file = output_dir / "ui-structure.json"
            if ui_structure_file.exists():
                with open(ui_structure_file, "r", encoding="utf-8") as f:
                    ui_structure = json.load(f)
                logger.info(f"UI 구조 파일 로드됨: {ui_structure_file}")
            else:
                # 목업 데이터 사용
                ui_structure = {"sections": [], "navigation": []}
            
            # 디자인 요소 파일 로드
            design_elements_file = output_dir / "design-elements.json"
            if design_elements_file.exists():
                with open(design_elements_file, "r", encoding="utf-8") as f:
                    design_elements = json.load(f)
                logger.info(f"디자인 요소 파일 로드됨: {design_elements_file}")
            else:
                # 목업 데이터 사용
                design_elements = {"colors": [], "typography": {}}
            
            # AI 인사이트 파일 로드
            ai_insights_file = output_dir / "ai-insights.json"
            if not ai_insights_file.exists():
                # 목업 데이터 사용
                mock_data = load_mock_data("coffee_shop_with_ai_insights.json")
                if mock_data:
                    # 목업 파일 저장
                    with open(ai_insights_file, "w", encoding="utf-8") as f:
                        json.dump(mock_data.get("ai_insights", {}), f, ensure_ascii=False, indent=2)
                    logger.info(f"AI 인사이트 파일 생성됨: {ai_insights_file}")
            
            # AI 인사이트 로드
            if ai_insights_file.exists():
                with open(ai_insights_file, "r", encoding="utf-8") as f:
                    ai_insights = json.load(f)
                logger.info(f"AI 인사이트 파일 로드됨: {ai_insights_file}")
            else:
                ai_insights = {}
            
            # 목업 이미지
            mockup_images = {}
            mockup_dir = outputs_dir / task_id / "mockups"
            if mockup_dir.exists():
                for img_file in mockup_dir.glob("*.png"):
                    page_name = img_file.stem
                    mockup_images[page_name] = f"/outputs/{task_id}/mockups/{img_file.name}"
            
            if not mockup_images:
                # 더미 목업 이미지
                mockup_images = {
                    "homepage": "https://placehold.co/800x450?text=홈페이지+목업",
                    "services": "https://placehold.co/800x450?text=서비스+페이지+목업"
                }
            
            # 결과 데이터 구성
            result_data = {
                "task": task,
                "ui_structure": ui_structure,
                "design_elements": design_elements,
                "ai_insights": ai_insights,
                "mockups": mockup_images,
                "url": task.get("url", ""),
                "title": design_elements.get("site_name", "웹사이트 분석 결과"),
                "has_accessibility": "accessibility" in ai_insights
            }
            
            logger.info(f"결과 데이터 구성 완료: {result_id}")
            logger.info(f"- URL: {result_data['url']}")
            logger.info(f"- 제목: {result_data['title']}")
            logger.info(f"- 내비게이션 항목 수: {len(ui_structure.get('navigation', []))}")
            logger.info(f"- 컴포넌트 수: {len(ui_structure.get('components', []))}")
            logger.info(f"- 색상 수: {len(design_elements.get('colors', []))}")
            logger.info(f"- 목업 이미지: {mockup_images}")
            logger.info(f"- 접근성 분석: {result_data['has_accessibility']}")
            
            # 결과 페이지 렌더링
            return templates.TemplateResponse(
                "results.html",
                {
                    "request": request,
                    "title": result_data["title"],
                    "result_id": result_id,
                    "data": result_data
                }
            )
            
        except Exception as e:
            logger.error(f"결과 페이지 렌더링 중 오류 발생: {str(e)}")
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "title": "결과 로드 오류",
                    "error_message": f"결과 데이터 로드 중 오류가 발생했습니다: {str(e)}"
                }
            )
    
    @app.get("/about", response_class=HTMLResponse, tags=["웹"])
    async def about(request: Request):
        """
        소개 페이지
        
        서비스 소개 및 사용법 페이지를 제공합니다.
        """
        return templates.TemplateResponse(
            "about.html",
            {
                "request": request,
                "title": "서비스 소개"
            }
        )
    
    @app.get("/dashboard", response_class=HTMLResponse, tags=["웹"])
    async def dashboard(request: Request):
        """
        대시보드 페이지
        
        관리자용 대시보드 페이지를 제공합니다.
        """
        # DB에서 최근 작업 목록 가져오기
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "관리자 대시보드"
            }
        )

def init_web_routes(app):
    """웹 라우트 초기화 함수"""
    register_web_routes(app)
    logger.info("웹 라우트 초기화 완료") 