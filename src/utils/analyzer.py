"""
웹사이트 분석 모듈

이 모듈은 웹사이트를 분석하고 기획서 생성을 위한 
데이터를 추출하는 기능을 제공합니다.
"""
import logging
import json
import asyncio
import os
from pathlib import Path
import httpx
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import uuid

# 내부 모듈 임포트
from src.utils.task_manager import update_task_status, update_step_status, get_task_status
from src.utils.mock_data_loader import load_mock_data
from src.utils.url_validator import validate_url, normalize_url
from src.utils.html_extractor import extract_html_metadata

# 로거 설정
logger = logging.getLogger(__name__)

async def analyze_website(url: str, task_id: str, use_mock: bool = False) -> None:
    """
    웹사이트를 분석하고 결과를 파일로 저장합니다.
    
    Args:
        url: 분석할 웹사이트 URL
        task_id: 작업 ID
        use_mock: 모의 데이터 사용 여부
    
    주의:
        이 함수는 백그라운드 작업으로 실행되어야 합니다.
    """
    try:
        # 작업 상태 업데이트
        update_task_status(task_id, status="running", message=f"분석 시작: {url}")
        
        # Step 1: 페이지 요청 및 HTML 다운로드
        update_step_status(task_id, 0, "running", "웹사이트 접속 중...")
        
        if use_mock:
            # 모의 데이터 사용 시 지연 시뮬레이션
            await asyncio.sleep(1)
            mock_data = load_mock_data("coffee_shop_with_ai_insights.json")
            if not mock_data:
                update_task_status(
                    task_id, 
                    status="error", 
                    message="모의 데이터 로드 실패",
                    error="모의 데이터 파일을 찾을 수 없습니다."
                )
                return
                
            update_step_status(task_id, 0, "completed", "웹사이트 접속 완료")
            
            # 모의 분석 과정 시뮬레이션
            for i in range(1, 7):
                step_name = get_step_name(i)
                update_step_status(task_id, i, "running", f"{step_name} 중...")
                await asyncio.sleep(1.5)  # 각 단계마다 지연
                update_step_status(task_id, i, "completed", f"{step_name} 완료")
            
            # 모의 결과 파일 저장
            await save_mock_results(task_id, mock_data, url)
            
            # 작업 완료 상태 업데이트
            update_task_status(
                task_id, 
                status="completed", 
                progress=100, 
                message="분석 완료", 
                result_id=f"result_{task_id}"
            )
            return
        
        # 실제 웹사이트 분석 시작
        # URL 유효성 검사
        if not validate_url(url):
            update_task_status(
                task_id, 
                status="error", 
                message="유효하지 않은 URL",
                error="입력한 URL이 올바르지 않습니다. http:// 또는 https://로 시작하는 유효한 URL을 입력하세요."
            )
            return
        
        # URL 정규화
        url = normalize_url(url)
        
        # 웹사이트 HTML 가져오기
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                logger.info(f"HTTP Request: GET {url}")
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text
                
                # 리다이렉트된 경우 최종 URL 업데이트
                if response.url != url:
                    url = str(response.url)
                    logger.info(f"URL 리다이렉트됨: {url}")
        except httpx.HTTPStatusError as e:
            update_task_status(
                task_id, 
                status="error", 
                message=f"HTTP 오류: {e.response.status_code}",
                error=f"웹사이트 접근 오류: HTTP {e.response.status_code} - {e.response.reason_phrase}"
            )
            return
        except httpx.RequestError as e:
            update_task_status(
                task_id, 
                status="error", 
                message="접속 오류",
                error=f"웹사이트 접속 오류: {str(e)}"
            )
            return
        except Exception as e:
            update_task_status(
                task_id, 
                status="error", 
                message="접속 오류",
                error=f"웹사이트 접속 중 오류 발생: {str(e)}"
            )
            return
        
        update_step_status(task_id, 0, "completed", "웹사이트 접속 완료")
        
        # Step 2: HTML 메타데이터 추출
        update_step_status(task_id, 1, "running", "메타데이터 추출 중...")
        metadata = extract_html_metadata(html_content, url)
        
        # 결과 저장 디렉토리 생성
        from src.app_config import outputs_dir
        output_dir = outputs_dir / task_id
        meta_dir = output_dir / "meta"
        os.makedirs(meta_dir, exist_ok=True)
        
        # HTML 저장
        with open(meta_dir / "source.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        update_step_status(task_id, 1, "completed", "메타데이터 추출 완료")
        
        # 향후 실제 분석 로직 구현 (현재는 모의 구현)
        # Step 3-7: 현재는 모의 데이터로 대체
        mock_data = load_mock_data("coffee_shop_with_ai_insights.json")
        if not mock_data:
            update_task_status(
                task_id, 
                status="error", 
                message="분석 데이터 생성 실패",
                error="분석 템플릿을 로드할 수 없습니다."
            )
            return
        
        # 실제 메타데이터로 업데이트
        mock_data.update({
            "url": url,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
        })
        
        # 나머지 단계 시뮬레이션
        for i in range(2, 7):
            step_name = get_step_name(i)
            update_step_status(task_id, i, "running", f"{step_name} 중...")
            await asyncio.sleep(1)  # 각 단계마다 지연
            update_step_status(task_id, i, "completed", f"{step_name} 완료")
            
        # 결과 파일 저장
        await save_mock_results(task_id, mock_data, url)
        
        # 작업 완료 상태 업데이트
        update_task_status(
            task_id, 
            status="completed", 
            progress=100, 
            message="분석 완료", 
            result_id=f"result_{task_id}"
        )
        
    except Exception as e:
        logger.error(f"웹사이트 분석 중 오류: {str(e)}")
        update_task_status(
            task_id, 
            status="error", 
            message="분석 중 오류 발생",
            error=f"분석 처리 중 예상치 못한 오류가 발생했습니다: {str(e)}"
        )

async def save_mock_results(task_id: str, mock_data: Dict[str, Any], url: str) -> None:
    """
    모의 분석 결과를 파일로 저장합니다.
    
    Args:
        task_id: 작업 ID
        mock_data: 모의 분석 결과 데이터
        url: 분석한 URL
    """
    from src.app_config import outputs_dir
    
    # 결과 디렉토리 생성
    output_dir = outputs_dir / task_id
    meta_dir = output_dir / "meta"
    mockup_dir = output_dir / "mockups"
    
    os.makedirs(meta_dir, exist_ok=True)
    os.makedirs(mockup_dir, exist_ok=True)
    
    # UI 구조 파일 저장
    ui_structure = {
        "url": url,
        "title": mock_data.get("title", "웹사이트 분석"),
        "description": mock_data.get("description", ""),
        "navigation": mock_data.get("navigation", []),
        "sections": mock_data.get("sections", []),
        "components": mock_data.get("components", [])
    }
    
    with open(meta_dir / "ui-structure.json", "w", encoding="utf-8") as f:
        json.dump(ui_structure, f, ensure_ascii=False, indent=2)
    
    # 디자인 요소 파일 저장
    design_elements = {
        "site_name": mock_data.get("title", "웹사이트"),
        "url": url,
        "colors": mock_data.get("colors", []),
        "typography": mock_data.get("typography", {}),
        "layout": mock_data.get("layout", "responsive"),
        "components": mock_data.get("components", [])
    }
    
    with open(meta_dir / "design-elements.json", "w", encoding="utf-8") as f:
        json.dump(design_elements, f, ensure_ascii=False, indent=2)
    
    # AI 인사이트 파일 저장
    ai_insights = {
        "overview": mock_data.get("overview", ""),
        "design_insights": mock_data.get("design_insights", ""),
        "functional_insights": mock_data.get("functional_insights", ""),
        "recommendations": mock_data.get("recommendations", []),
        "tech_stack": mock_data.get("tech_stack", []),
        "accessibility": mock_data.get("accessibility", {}),
        "competitors": mock_data.get("competitors", []),
        "strengths": mock_data.get("strengths", []),
        "weaknesses": mock_data.get("weaknesses", [])
    }
    
    with open(meta_dir / "ai-insights.json", "w", encoding="utf-8") as f:
        json.dump(ai_insights, f, ensure_ascii=False, indent=2)
    
    # 목업 이미지 생성 (실제로는 외부 API 사용, 지금은 연결로만 대체)
    from src.app_config import static_dir
    
    # 기본 목업 이미지 파일 복사 (개발용)
    # 실제 애플리케이션에서는 이 부분이 실제 목업 생성 코드로 대체됨
    sample_mockup = static_dir / "img" / "sample_mockup.png"
    if sample_mockup.exists():
        import shutil
        shutil.copy(sample_mockup, mockup_dir / "homepage.png")
        shutil.copy(sample_mockup, mockup_dir / "subpage.png")

def get_step_name(step_index: int) -> str:
    """
    단계 인덱스에 해당하는 단계 이름을 반환합니다.
    
    Args:
        step_index: 단계 인덱스 (0부터 시작)
        
    Returns:
        str: 단계 이름
    """
    steps = [
        "페이지 구조 분석",
        "콘텐츠 추출 및 분류",
        "메뉴 및 내비게이션 분석",
        "디자인 요소 추출",
        "기획서 생성",
        "목업 이미지 생성",
        "아이디어 제안 생성"
    ]
    
    if 0 <= step_index < len(steps):
        return steps[step_index]
    else:
        return f"단계 {step_index}" 