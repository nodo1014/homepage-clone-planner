"""
내보내기 관련 엔드포인트

이 모듈은 분석 결과를 다운로드하거나 이메일로 전송하는 등의 내보내기 기능을 위한 
FastAPI 라우트를 제공합니다.
"""
import os
import json
import logging
from pathlib import Path
from fastapi import Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# 내부 모듈 임포트
from src.app_config import base_dir, outputs_dir as RESULTS_DIR, exports_dir as EXPORTS_DIR, templates
from src.app_config import base_dir, templates_dir
from src.app_config import DOTENV_PATH, EMAIL_TEMPLATE_PATH

from src.utils.task_manager import get_task_status
from src.export.export_manager import ExportManager
from src.export.email_sender import EmailSender, send_analysis_results

# 로거 설정
logger = logging.getLogger(__name__)

def register_export_routes(app):
    """내보내기 관련 라우트 등록"""
    
    @app.get("/download/{result_id}/{type}", response_class=FileResponse, tags=["내보내기"])
    async def download_results(request: Request, result_id: str, type: str):
        """
        결과 다운로드
        
        - **result_id**: 결과 ID
        - **type**: 다운로드 유형 (plan, design, ideas, zip)
        
        분석 결과를 지정한 형식으로 다운로드합니다.
        """
        # 결과 ID에서 task_id 추출 (예: result_abc123 -> abc123)
        task_id = result_id.replace("result_", "")
        
        # 작업 상태 확인
        task = get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
        
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="분석이 완료되지 않았습니다")
        
        # 메타데이터 파일 경로
        meta_dir = Path(base_dir) / "outputs" / task_id / "meta"
        output_dir = Path(base_dir) / "outputs" / task_id / "downloads"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 내보내기 관리자 생성
        export_manager = ExportManager(output_dir)
        
        try:
            # UI 구조 데이터
            ui_structure_path = meta_dir / "ui-structure.json"
            if ui_structure_path.exists():
                with open(ui_structure_path, "r", encoding="utf-8") as f:
                    ui_structure = json.load(f)
            else:
                raise HTTPException(status_code=404, detail="분석 결과 데이터를 찾을 수 없습니다")
            
            # 디자인 요소 데이터
            design_path = meta_dir / "design-elements.json"
            if design_path.exists():
                with open(design_path, "r", encoding="utf-8") as f:
                    design_data = json.load(f)
            else:
                design_data = {}
            
            # 내보내기용 콘텐츠 구성
            content = {
                "title": f"{ui_structure.get('title', '웹사이트')} 클론 기획서",
                "description": ui_structure.get("description", "웹사이트 분석 결과입니다."),
                "website": {
                    "name": ui_structure.get("title", "웹사이트"),
                    "url": ui_structure.get("url", "https://example.com"),
                    "description": ui_structure.get("description", "")
                },
                "structure": {
                    "header": {
                        "logo": True,
                        "navigation": len(ui_structure.get("nav", [])) > 0
                    },
                    "main_sections": [page.get("title", "페이지") for page in ui_structure.get("pages", [])],
                    "footer": {
                        "copyright": True,
                        "social_links": False,
                        "contact_info": False
                    }
                },
                "design_analysis": {
                    "colors": design_data.get("colors", []),
                    "fonts": design_data.get("fonts", [{"name": "기본 폰트", "usage": "본문"}]),
                    "layout": design_data.get("layout_type", "표준 레이아웃")
                },
                "development_recommendations": "웹사이트의 디자인과 구조를 분석한 결과, 모바일 최적화와 접근성을 고려한 개발이 필요합니다.",
                "conclusion": "이 웹사이트의 클론 개발은 약 2주 정도 소요될 것으로 예상됩니다."
            }
            
            # 파일 형식에 따라 내보내기
            if type == "zip":
                # 모든 형식을 포함한 ZIP 파일 생성
                file_path = export_manager.export_to_zip(content, f"{task_id}_all")
                return FileResponse(
                    path=file_path,
                    filename=f"{ui_structure.get('title', 'website')}_clone_plan.zip",
                    media_type="application/zip"
                )
            elif type == "plan":
                # 마크다운 형식의 기획서
                file_path = export_manager.export_to_markdown(content, f"{task_id}_plan")
                return FileResponse(
                    path=file_path,
                    filename=f"{ui_structure.get('title', 'website')}_plan.md",
                    media_type="text/markdown"
                )
            elif type == "design":
                # 디자인 요소 정보 (JSON)
                file_path = export_manager.export_to_json(design_data, f"{task_id}_design")
                return FileResponse(
                    path=file_path,
                    filename=f"{ui_structure.get('title', 'website')}_design.json",
                    media_type="application/json"
                )
            elif type == "ideas":
                # 아이디어 정보 (마크다운)
                ideas_content = {
                    "title": f"{ui_structure.get('title', '웹사이트')} 개선 아이디어",
                    "website": content["website"],
                    "overview": "이 문서는 웹사이트 분석을 기반으로 한 개선 아이디어를 제공합니다.",
                    "development_recommendations": content["development_recommendations"]
                }
                file_path = export_manager.export_to_markdown(ideas_content, f"{task_id}_ideas")
                return FileResponse(
                    path=file_path,
                    filename=f"{ui_structure.get('title', 'website')}_ideas.md",
                    media_type="text/markdown"
                )
            else:
                raise HTTPException(status_code=400, detail=f"지원하지 않는 다운로드 유형: {type}")
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"다운로드 중 오류 발생: {str(e)}")

    @app.get("/export/{result_id}/{format_type}", tags=["내보내기"])
    async def export_results(result_id: str, format_type: str, request: Request):
        """
        분석 결과를 지정한 형식으로 내보내기
        
        - **result_id**: 결과 ID
        - **format_type**: 내보내기 형식 (markdown, html, pdf, pptx, json, zip, notion, gdrive)
        
        지정한 형식으로 결과를 내보내거나 외부 서비스(노션, 구글 드라이브)로 내보냅니다.
        """
        try:
            # 결과 파일 경로
            result_path = RESULTS_DIR / f"{result_id}.json"
            if not result_path.exists():
                raise HTTPException(status_code=404, detail=f"결과 ID {result_id}를 찾을 수 없습니다.")
            
            # 결과 데이터 로드
            with open(result_path, "r", encoding="utf-8") as f:
                result_content = json.load(f)
            
            # 내보내기 형식 검증
            format_type = format_type.lower()
            supported_formats = ['markdown', 'md', 'html', 'pdf', 'pptx', 'json', 'zip', 'notion', 'gdrive']
            if format_type not in supported_formats:
                raise HTTPException(status_code=400, detail=f"지원하지 않는 내보내기 형식: {format_type}")
            
            # 내보내기 관리자 설정
            export_manager = ExportManager(EXPORTS_DIR)
            
            # 노션 내보내기는 특별 처리 (URL 반환)
            if format_type == 'notion':
                # 노션 내보내기 필수 설정 확인
                parent_id = os.getenv("NOTION_PARENT_PAGE_ID")
                api_key = os.getenv("NOTION_API_KEY")
                
                # 설정 누락 시 오류 응답
                if not parent_id or not api_key:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "message": "노션 연동에 필요한 설정이 누락되었습니다. 환경 변수 NOTION_PARENT_PAGE_ID와 NOTION_API_KEY를 확인하세요."
                        }
                    )
                
                # 노션으로 내보내기
                try:
                    page_url = export_manager.export_to_notion(
                        content=result_content,
                        parent_id=parent_id,
                        api_key=api_key
                    )
                    
                    # 성공 시 URL 반환
                    return JSONResponse(
                        content={
                            "status": "success",
                            "message": "노션 페이지로 내보내기가 완료되었습니다.",
                            "url": page_url
                        }
                    )
                except Exception as e:
                    # 내보내기 실패 시 오류 반환
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "message": f"노션 페이지로 내보내기 실패: {str(e)}"
                        }
                    )

            # 구글 드라이브 내보내기는 특별 처리 (URL 반환)
            elif format_type == 'gdrive':
                # 구글 드라이브 내보내기 필수 설정 확인
                credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
                
                # 설정 누락 시 오류 응답
                if not credentials_file or not os.path.exists(credentials_file):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "message": "구글 드라이브 연동에 필요한 설정이 누락되었습니다. 환경 변수 GOOGLE_CREDENTIALS_FILE을 확인하세요."
                        }
                    )
                
                # 구글 드라이브로 내보내기 형식 설정
                export_format = 'markdown'  # 기본값: 마크다운
                
                # 구글 드라이브로 내보내기
                try:
                    # 웹사이트 이름 추출
                    website_name = result_content.get('website', {}).get('name', '웹사이트')
                    folder_name = f"{website_name} 클론 기획서"
                    
                    drive_url = export_manager.export_to_google_drive(
                        content=result_content,
                        filename=f"{result_id}_plan",
                        folder_name=folder_name,
                        export_format=export_format,
                        credentials_file=credentials_file
                    )
                    
                    # 성공 시 URL 반환
                    return JSONResponse(
                        content={
                            "status": "success",
                            "message": "구글 드라이브로 내보내기가 완료되었습니다.",
                            "url": drive_url
                        }
                    )
                except Exception as e:
                    # 내보내기 실패 시 오류 반환
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "message": f"구글 드라이브로 내보내기 실패: {str(e)}"
                        }
                    )
            
            # 다른 모든 형식은 파일 다운로드 처리
            filename = f"{result_id}_{format_type}"
            file_path = export_manager.export_to_format(result_content, filename, format_type)
            
            # 파일 다운로드 URL로 리다이렉트
            download_url = f"/download/{os.path.basename(file_path)}"
            return RedirectResponse(url=download_url, status_code=303)
            
        except HTTPException:
            raise
        except Exception as e:
            # 일반 오류 처리
            raise HTTPException(status_code=500, detail=f"내보내기 처리 중 오류 발생: {str(e)}")

    @app.post("/send-email/{result_id}", tags=["내보내기"])
    async def send_email_results(result_id: str, email: str = Form(...), background_tasks: BackgroundTasks = None):
        """
        분석 결과를 이메일로 전송
        
        - **result_id**: 결과 ID
        - **email**: 수신자 이메일 주소
        
        분석 결과를 첨부 파일과 함께 지정된 이메일 주소로 전송합니다.
        """
        try:
            # 결과 데이터 로드
            result_path = RESULTS_DIR / f"{result_id}.json"
            if not result_path.exists():
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": f"결과 ID {result_id}를 찾을 수 없습니다."}
                )
            
            with open(result_path, "r", encoding="utf-8") as f:
                result_content = json.load(f)
            
            # 첨부할 파일 목록 준비
            export_manager = ExportManager(EXPORTS_DIR)
            result_files = []
            
            # 마크다운 파일 생성 및 첨부
            try:
                md_file = export_manager.export_to_format(result_content, f"{result_id}_plan", format="markdown")
                result_files.append(md_file)
            except Exception as e:
                logger.error(f"마크다운 생성 오류: {str(e)}")
            
            # JSON 파일 생성 및 첨부
            try:
                json_file = export_manager.export_to_format(result_content, f"{result_id}_data", format="json")
                result_files.append(json_file)
            except Exception as e:
                logger.error(f"JSON 생성 오류: {str(e)}")
            
            # 모든 파일을 ZIP으로 압축하여 첨부
            try:
                zip_file = export_manager.export_to_format(result_content, f"{result_id}_all", format="zip")
                result_files.append(zip_file)
            except Exception as e:
                logger.error(f"ZIP 생성 오류: {str(e)}")
            
            # 이메일 전송 함수 정의
            async def send_email_task():
                try:
                    # 백그라운드에서 이메일 전송
                    success = await send_analysis_results(
                        to_email=email,
                        result_content=result_content,
                        result_files=result_files,
                        template_path=EMAIL_TEMPLATE_PATH
                    )
                    
                    logger.info(f"이메일 전송 결과: {success}")
                    return success
                except Exception as e:
                    logger.error(f"이메일 전송 오류: {str(e)}")
                    return False
            
            if background_tasks:
                # 백그라운드에서 이메일 전송
                background_tasks.add_task(send_email_task)
                response_message = f"{email} 주소로 결과를 전송하고 있습니다."
            else:
                # 동기적으로 이메일 전송
                email_sender = EmailSender()
                success = email_sender.send_results_email(
                    to_email=email,
                    subject=f"홈페이지 클론 기획서 - {result_content.get('title', '분석 결과')}",
                    result_content=result_content,
                    result_files=result_files,
                    template_path=EMAIL_TEMPLATE_PATH
                )
                
                response_message = f"{email} 주소로 결과가 전송되었습니다." if success else "이메일 전송 중 오류가 발생했습니다."
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": response_message
                }
            )
        
        except Exception as e:
            logger.error(f"이메일 전송 처리 오류: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"이메일 전송 처리 중 오류가 발생했습니다: {str(e)}"}
            )

def init_export_routes(app):
    """내보내기 라우트 초기화"""
    register_export_routes(app)
    logger.info("내보내기 라우트 초기화 완료") 