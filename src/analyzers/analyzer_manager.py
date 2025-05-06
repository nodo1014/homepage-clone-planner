"""
웹사이트 분석 관리자 모듈

이 모듈은 웹사이트 분석 프로세스를 관리하고 조율합니다.
"""
import logging
import asyncio
from typing import Dict, List, Any, Tuple, Optional
import os
import json
from pathlib import Path
from datetime import datetime

# 다른 모듈 임포트
from src.utils import task_manager
from src.utils.html_extractor import fetch_page, analyze_page, fetch_and_analyze
from src.analyzer.fetcher import fetch_website_content, fetch_website_content_async
from src.analyzer.analyzer import analyze_website
from src.analyzer.ai_analyzer import ai_analyze_website

# 로거 설정
logger = logging.getLogger(__name__)

class AnalyzerManager:
    """웹사이트 분석 관리 클래스"""
    
    def __init__(self, output_dir: str = None):
        """
        분석 관리자 초기화
        
        Args:
            output_dir: 결과 저장 디렉토리 경로
        """
        self.output_dir = Path(output_dir) if output_dir else Path(os.getcwd()) / "outputs"
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        logger.info(f"분석 관리자 초기화: 출력 디렉토리={self.output_dir}")
    
    async def analyze_website(self, task_id: str, url: str) -> Tuple[bool, Dict[str, Any]]:
        """
        웹사이트 분석 수행
        
        Args:
            task_id: 분석 작업 ID
            url: 분석할 웹사이트 URL
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (성공 여부, 분석 결과)
        """
        try:
            # 작업 디렉토리 생성
            task_dir = self.output_dir / task_id
            task_dir.mkdir(exist_ok=True)
            
            # 작업 상태 업데이트
            task_manager.update_task_status(
                task_id, 
                status="running", 
                progress=5, 
                message="웹사이트 콘텐츠 가져오는 중..."
            )
            task_manager.update_step_status(
                task_id, 
                0, 
                "running", 
                "웹페이지 다운로드 중"
            )
            
            # 웹사이트 콘텐츠 가져오기
            success, content = await fetch_website_content_async(url)
            
            if not success:
                logger.error(f"웹사이트 콘텐츠 가져오기 실패: {url} - {content}")
                
                task_manager.update_task_status(
                    task_id, 
                    status="error", 
                    progress=0, 
                    message="콘텐츠 가져오기 실패", 
                    error=str(content)
                )
                task_manager.update_step_status(
                    task_id, 
                    0, 
                    "error", 
                    f"웹페이지 다운로드 실패: {content}"
                )
                
                return False, {"error": str(content)}
            
            task_manager.update_step_status(
                task_id, 
                0, 
                "completed", 
                "웹페이지 다운로드 완료"
            )
            task_manager.update_task_status(
                task_id, 
                status="running", 
                progress=20, 
                message="웹사이트 구조 분석 중..."
            )
            task_manager.update_step_status(
                task_id, 
                1, 
                "running", 
                "HTML 구조 분석 중"
            )
            
            # 웹사이트 콘텐츠 저장 (옵션)
            # content_path = task_dir / "content.html"
            # with open(content_path, "w", encoding="utf-8") as f:
            #     f.write(content)
            
            # 웹사이트 기본 분석
            result = await analyze_website(url)
            
            if not result[0]:  # 분석 실패
                logger.error(f"웹사이트 분석 실패: {url} - {result[1]['error']}")
                
                task_manager.update_task_status(
                    task_id, 
                    status="error", 
                    progress=20, 
                    message="분석 실패", 
                    error=result[1]['error']
                )
                task_manager.update_step_status(
                    task_id, 
                    1, 
                    "error", 
                    f"HTML 구조 분석 실패: {result[1]['error']}"
                )
                
                return False, result[1]
            
            # 분석 결과
            analysis_result = result[1]
            
            task_manager.update_step_status(
                task_id, 
                1, 
                "completed", 
                "HTML 구조 분석 완료"
            )
            task_manager.update_task_status(
                task_id, 
                status="running", 
                progress=40, 
                message="웹사이트 디자인 요소 분석 중..."
            )
            task_manager.update_step_status(
                task_id, 
                2, 
                "running", 
                "색상 및 스타일 분석 중"
            )
            
            # 웹사이트 디자인 분석
            design_result = {
                "colors": analysis_result.get("colors", []),
                "fonts": analysis_result.get("fonts", []),
                "layout": analysis_result.get("layout", {}),
                "components": analysis_result.get("components", [])
            }
            
            task_manager.update_step_status(
                task_id, 
                2, 
                "completed", 
                "색상 및 스타일 분석 완료"
            )
            task_manager.update_task_status(
                task_id, 
                status="running", 
                progress=60, 
                message="웹사이트 콘텐츠 분석 중..."
            )
            task_manager.update_step_status(
                task_id, 
                3, 
                "running", 
                "페이지 콘텐츠 및 구조 분석 중"
            )
            
            # 콘텐츠 구조 분석
            content_structure = {
                "pages": analysis_result.get("pages", []),
                "menu": analysis_result.get("menu", []),
                "sections": analysis_result.get("sections", [])
            }
            
            task_manager.update_step_status(
                task_id, 
                3, 
                "completed", 
                "페이지 콘텐츠 및 구조 분석 완료"
            )
            task_manager.update_task_status(
                task_id, 
                status="running", 
                progress=80, 
                message="AI 기반 분석 및 요약 생성 중..."
            )
            task_manager.update_step_status(
                task_id, 
                4, 
                "running", 
                "AI 분석 및 인사이트 생성 중"
            )
            
            # AI 분석 (선택적)
            try:
                ai_result = await ai_analyze_website(analysis_result)
                
                # AI 분석 결과 병합
                analysis_result["ai_insights"] = ai_result
            except Exception as e:
                logger.warning(f"AI 분석 건너뜀: {str(e)}")
                analysis_result["ai_insights"] = {"error": str(e)}
            
            task_manager.update_step_status(
                task_id, 
                4, 
                "completed", 
                "AI 분석 및 인사이트 생성 완료"
            )
            task_manager.update_task_status(
                task_id, 
                status="running", 
                progress=90, 
                message="결과 정리 및 저장 중..."
            )
            task_manager.update_step_status(
                task_id, 
                5, 
                "running", 
                "최종 보고서 및 메타데이터 생성 중"
            )
            
            # 결과 저장
            # 메타 디렉토리 생성
            meta_dir = task_dir / "meta"
            meta_dir.mkdir(exist_ok=True)
            
            # UI 구조 데이터 저장
            ui_structure = {
                "url": url,
                "title": analysis_result.get("metadata", {}).get("title", ""),
                "description": analysis_result.get("metadata", {}).get("description", ""),
                "pages": analysis_result.get("pages", []),
                "nav": analysis_result.get("menu", []),
                "components": analysis_result.get("components", []),
                "layout": analysis_result.get("layout", {})
            }
            
            with open(meta_dir / "ui-structure.json", "w", encoding="utf-8") as f:
                json.dump(ui_structure, f, ensure_ascii=False, indent=2)
            
            # 디자인 요소 데이터 저장
            with open(meta_dir / "design-elements.json", "w", encoding="utf-8") as f:
                json.dump(design_result, f, ensure_ascii=False, indent=2)
            
            # 콘텐츠 구조 데이터 저장
            with open(meta_dir / "content-structure.json", "w", encoding="utf-8") as f:
                json.dump(content_structure, f, ensure_ascii=False, indent=2)
            
            # 전체 분석 결과 저장
            with open(task_dir / "analysis-result.json", "w", encoding="utf-8") as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)
            
            task_manager.update_step_status(
                task_id, 
                5, 
                "completed", 
                "최종 보고서 및 메타데이터 생성 완료"
            )
            task_manager.update_step_status(
                task_id, 
                6, 
                "completed", 
                "분석 완료"
            )
            
            # 작업 완료 상태 업데이트
            result_id = f"result_{task_id}"
            task_manager.update_task_status(
                task_id, 
                status="completed", 
                progress=100, 
                message="분석 완료!", 
                result_id=result_id
            )
            
            return True, analysis_result
            
        except Exception as e:
            logger.error(f"웹사이트 분석 중 오류 발생: {str(e)}")
            
            # 오류 상태 업데이트
            task_manager.update_task_status(
                task_id, 
                status="error", 
                message="분석 중 오류 발생", 
                error=str(e)
            )
            
            return False, {"error": str(e)}

# 싱글톤 인스턴스
_analyzer_manager = None

def get_analyzer_manager(output_dir: str = None) -> AnalyzerManager:
    """
    분석 관리자 싱글톤 인스턴스 가져오기
    
    Args:
        output_dir: 결과 저장 디렉토리 경로
        
    Returns:
        AnalyzerManager: 분석 관리자 인스턴스
    """
    global _analyzer_manager
    
    if _analyzer_manager is None:
        _analyzer_manager = AnalyzerManager(output_dir)
    
    return _analyzer_manager

async def analyze_website_task(task_id: str, url: str) -> bool:
    """
    웹사이트 분석 작업 수행
    
    Args:
        task_id: 분석 작업 ID
        url: 분석할 웹사이트 URL
        
    Returns:
        bool: 성공 여부
    """
    # 분석 관리자 가져오기
    analyzer = get_analyzer_manager()
    
    # 웹사이트 분석 수행
    success, _ = await analyzer.analyze_website(task_id, url)
    
    return success 