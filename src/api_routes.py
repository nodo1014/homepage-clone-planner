"""
API 관련 엔드포인트

이 모듈은 API 문서, 스키마 등의 API 관련 엔드포인트를 제공합니다.
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import json
from pathlib import Path
from typing import Dict, Any

# 내부 모듈 임포트
from src.app_config import app, templates, DOCS_DIR
from src.utils.api_docs_generator import generate_api_docs

# 로거 설정
logger = logging.getLogger(__name__)

def register_api_routes(app):
    """API 관련 라우트 등록"""
    
    @app.get("/api/docs", response_class=HTMLResponse, tags=["API"])
    async def api_docs_html(request: Request):
        """API 문서 HTML 버전 제공"""
        try:
            # 문서 파일 생성 (없는 경우)
            docs_file = DOCS_DIR / "api_docs.html"
            if not docs_file.exists():
                html_content = generate_api_docs(format="html")
                docs_file.write_text(html_content, encoding="utf-8")
            
            # HTML 파일 읽기
            with open(docs_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # HTML 응답 반환
            return HTMLResponse(content=html_content)
        except Exception as e:
            # 오류 발생 시
            error_message = f"API 문서 로드 중 오류 발생: {str(e)}"
            return templates.TemplateResponse(
                "error.html", 
                {"request": request, "title": "API 문서 오류", "error": error_message}
            )

    @app.get("/api/docs/md", response_class=FileResponse, tags=["API"])
    async def api_docs_markdown():
        """API 문서를 마크다운 형식으로 다운로드"""
        # 마크다운 문서 생성 (파일이 없거나 서버 재시작 후 처음 요청 시 생성)
        md_path = DOCS_DIR / "api_docs.md"
        if not md_path.exists():
            # 문서 생성
            doc_content = generate_api_docs(format="markdown")
            md_path.write_text(doc_content, encoding="utf-8")
        
        # 파일 다운로드 응답
        return FileResponse(
            path=md_path, 
            filename="홈페이지_클론_기획서_생성기_API_문서.md",
            media_type="text/markdown"
        )

    @app.get("/api/docs/regenerate", response_class=JSONResponse, tags=["API"])
    async def regenerate_api_docs():
        """API 문서를 강제로 다시 생성"""
        try:
            # 문서 생성
            html_content = generate_api_docs(format="html")
            md_content = generate_api_docs(format="markdown")
            
            # 파일 저장
            html_path = DOCS_DIR / "api_docs.html"
            md_path = DOCS_DIR / "api_docs.md"
            
            html_path.write_text(html_content, encoding="utf-8")
            md_path.write_text(md_content, encoding="utf-8")
            
            # 결과 반환
            return {
                "status": "success",
                "message": "API 문서가 성공적으로 다시 생성되었습니다.",
                "files": [str(html_path), str(md_path)]
            }
        except Exception as e:
            # 오류 발생 시
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"API 문서 생성 중 오류 발생: {str(e)}"
                }
            )

    @app.get("/api/schema", response_class=JSONResponse, tags=["API"])
    async def api_schema():
        """API 스키마 및 구조 정보"""
        schema = {
            "api_version": "1.0.0",
            "endpoints": [
                {
                    "path": "/analyze",
                    "method": "POST",
                    "description": "웹사이트 URL 분석",
                    "parameters": [
                        {"name": "url", "type": "string", "required": True, "description": "분석할 웹사이트 URL"}
                    ],
                    "response": {"type": "task_id", "description": "분석 작업의 고유 ID"}
                },
                {
                    "path": "/analyze/status/{task_id}",
                    "method": "GET",
                    "description": "분석 작업 상태 확인",
                    "parameters": [
                        {"name": "task_id", "type": "string", "required": True, "description": "분석 작업 ID"}
                    ],
                    "response": {"type": "object", "description": "작업 상태 정보"}
                },
                {
                    "path": "/api/structure/{task_id}",
                    "method": "GET",
                    "description": "웹사이트 구조 메타데이터 요청",
                    "parameters": [
                        {"name": "task_id", "type": "string", "required": True, "description": "분석 작업 ID"}
                    ],
                    "response": {"type": "object", "description": "웹사이트 구조 메타데이터"}
                }
            ],
            "schemas": {
                "ui_structure": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "pages": {"type": "array", "items": {"type": "object"}},
                        "nav": {"type": "array", "items": {"type": "object"}},
                        "components": {"type": "array", "items": {"type": "object"}},
                        "layout": {"type": "object"}
                    }
                },
                "design_elements": {
                    "type": "object",
                    "properties": {
                        "colors": {"type": "array", "items": {"type": "object"}},
                        "layout_type": {"type": "string"},
                        "components": {"type": "array", "items": {"type": "object"}},
                        "style_patterns": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        }
        return schema

    @app.get("/api/structure/{task_id}", response_class=JSONResponse, tags=["API"])
    async def get_structure(task_id: str):
        """
        웹사이트 구조 메타데이터 제공
        
        - **task_id**: 분석 작업 ID
        
        분석된 웹사이트의 구조, 디자인, 콘텐츠 메타데이터를 JSON 형식으로 제공합니다.
        """
        # 작업 상태 확인
        from src.utils.task_manager import get_task_status
        task = get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
        
        if task["status"] != "completed":
            return {
                "status": task["status"],
                "progress": task["progress"],
                "message": task["message"]
            }
        
        # UI 구조 JSON 파일 경로
        output_dir = Path(app.outputs_dir) / task_id / "meta"
        
        try:
            # UI 구조 데이터
            ui_structure_path = output_dir / "ui-structure.json"
            if ui_structure_path.exists():
                with open(ui_structure_path, "r", encoding="utf-8") as f:
                    ui_structure = json.load(f)
            else:
                ui_structure = {}
            
            # 디자인 요소 데이터
            design_path = output_dir / "design-elements.json"
            if design_path.exists():
                with open(design_path, "r", encoding="utf-8") as f:
                    design_data = json.load(f)
            else:
                design_data = {}
            
            # 콘텐츠 구조 데이터
            content_path = output_dir / "content-structure.json"
            if content_path.exists():
                with open(content_path, "r", encoding="utf-8") as f:
                    content_structure = json.load(f)
            else:
                content_structure = {}
            
            # 통합 데이터 반환
            return {
                "status": "success",
                "task_id": task_id,
                "ui_structure": ui_structure,
                "design_elements": design_data,
                "content_structure": content_structure
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"메타데이터 로드 실패: {str(e)}"
            }

def init_api_routes(app):
    """API 라우트 초기화"""
    register_api_routes(app)
    logger.info("API 라우트 초기화 완료") 