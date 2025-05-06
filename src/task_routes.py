"""
작업 관리 관련 엔드포인트

이 모듈은 웹사이트 분석 작업 상태 확인, 작업 관리 등의 기능을 위한 FastAPI 라우트를 제공합니다.
"""
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse

# 내부 모듈 임포트
from src.app_config import base_dir, templates
from src.utils.task_manager import get_task_status, get_all_tasks, delete_task

# 로거 설정
logger = logging.getLogger(__name__)

def register_task_routes(app):
    """작업 관리 관련 라우트 등록"""
    
    @app.get("/tasks", response_class=HTMLResponse, tags=["작업"])
    async def list_tasks(request: Request):
        """
        작업 목록 조회
        
        모든 작업 목록을 표시하는 관리 페이지입니다.
        """
        # 모든 작업 가져오기
        tasks = get_all_tasks()
        
        # 작업을 최신순으로 정렬
        sorted_tasks = sorted(
            tasks.values(),
            key=lambda t: t.get("created_at", datetime.now()), 
            reverse=True
        )
        
        # 템플릿 반환
        return templates.TemplateResponse(
            "tasks.html",
            {
                "request": request,
                "title": "작업 관리",
                "tasks": sorted_tasks
            }
        )
    
    @app.get("/api/tasks", response_class=JSONResponse, tags=["작업"])
    async def get_tasks_api():
        """
        작업 목록 API
        
        모든 작업 목록을 JSON 형식으로 반환합니다.
        """
        # 모든 작업 가져오기
        tasks = get_all_tasks()
        
        # JSON 직렬화를 위해 datetime 객체를 문자열로 변환
        serializable_tasks = {}
        for task_id, task in tasks.items():
            serializable_task = task.copy()
            
            # datetime 객체 ISO 형식으로 변환
            if isinstance(task.get("created_at"), datetime):
                serializable_task["created_at"] = task["created_at"].isoformat()
            if isinstance(task.get("updated_at"), datetime):
                serializable_task["updated_at"] = task["updated_at"].isoformat()
                
            serializable_tasks[task_id] = serializable_task
            
        return {"tasks": serializable_tasks}
    
    @app.delete("/api/tasks/{task_id}", response_class=JSONResponse, tags=["작업"])
    async def delete_task_api(task_id: str):
        """
        작업 삭제 API
        
        - **task_id**: 삭제할 작업 ID
        
        지정된 작업을 삭제합니다.
        """
        try:
            # 작업 존재 여부 확인
            task = get_task_status(task_id)
            if not task:
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": f"작업 {task_id}를 찾을 수 없습니다."}
                )
            
            # 작업 삭제
            delete_task(task_id)
            
            return JSONResponse(
                content={"status": "success", "message": f"작업 {task_id}가 삭제되었습니다."}
            )
        except Exception as e:
            logger.error(f"작업 삭제 중 오류 발생: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"작업 삭제 중 오류가 발생했습니다: {str(e)}"}
            )
    
    @app.get("/api/tasks/{task_id}", response_class=JSONResponse, tags=["작업"])
    async def get_task_api(task_id: str):
        """
        단일 작업 상태 API
        
        - **task_id**: 조회할 작업 ID
        
        특정 작업의 상세 정보를 반환합니다.
        """
        task = get_task_status(task_id)
        
        if not task:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": f"작업 {task_id}를 찾을 수 없습니다."}
            )
        
        # datetime 객체 ISO 형식으로 변환
        serializable_task = task.copy()
        if isinstance(task.get("created_at"), datetime):
            serializable_task["created_at"] = task["created_at"].isoformat()
        if isinstance(task.get("updated_at"), datetime):
            serializable_task["updated_at"] = task["updated_at"].isoformat()
            
        return serializable_task
    
    @app.get("/api/tasks/status/summary", response_class=JSONResponse, tags=["작업"])
    async def get_tasks_summary_api():
        """
        작업 상태 요약 API
        
        모든 작업의 상태 통계를 반환합니다.
        """
        # 모든 작업 가져오기
        tasks = get_all_tasks()
        
        # 상태별 작업 수 계산
        status_counts = {
            "total": len(tasks),
            "completed": sum(1 for t in tasks.values() if t.get("status") == "completed"),
            "running": sum(1 for t in tasks.values() if t.get("status") == "running"),
            "error": sum(1 for t in tasks.values() if t.get("status") == "error"),
            "pending": sum(1 for t in tasks.values() if t.get("status") == "pending"),
            "recent": sum(1 for t in tasks.values() if t.get("created_at") and 
                          isinstance(t["created_at"], datetime) and 
                          t["created_at"] > datetime.now() - timedelta(days=1))
        }
        
        return status_counts
    
    @app.post("/api/tasks/clean", response_class=JSONResponse, tags=["작업"])
    async def clean_old_tasks_api(days: int = 7):
        """
        오래된 작업 정리 API
        
        - **days**: 보존할 작업 기간 (일)
        
        지정된 일수보다 오래된 작업을 삭제합니다.
        """
        try:
            # 모든 작업 가져오기
            tasks = get_all_tasks()
            
            now = datetime.now()
            cutoff_date = now - timedelta(days=days)
            
            deleted_count = 0
            for task_id, task in list(tasks.items()):
                created_at = task.get("created_at")
                
                # datetime 객체인 경우에만 비교
                if isinstance(created_at, datetime) and created_at < cutoff_date:
                    delete_task(task_id)
                    deleted_count += 1
            
            return JSONResponse(
                content={
                    "status": "success", 
                    "message": f"{deleted_count}개의 오래된 작업이 삭제되었습니다.",
                    "deleted_count": deleted_count
                }
            )
            
        except Exception as e:
            logger.error(f"작업 정리 중 오류 발생: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"작업 정리 중 오류가 발생했습니다: {str(e)}"}
            )

def init_task_routes(app):
    """작업 관리 라우트 초기화"""
    register_task_routes(app)
    logger.info("작업 관리 라우트 초기화 완료") 