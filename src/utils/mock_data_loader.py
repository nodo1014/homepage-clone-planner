"""
목 데이터 로더 유틸리티

이 모듈은 ai_analysis 폴더의 예제 데이터를 로드하여 결과 페이지에 표시합니다.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# 로거 설정
logger = logging.getLogger(__name__)

def load_mock_data(filename: str) -> Dict[str, Any]:
    """
    지정된 목 데이터 파일 로드
    
    Args:
        filename: 로드할 목 데이터 파일명 (outputs/ai_analysis 디렉토리에서 찾음)
        
    Returns:
        Dict[str, Any]: 로드된 목 데이터 또는 실패 시 빈 딕셔너리
    """
    try:
        # 프로젝트 루트 경로 찾기
        root_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # AI 분석 데이터 파일 경로
        ai_analysis_dir = root_dir / "outputs" / "ai_analysis"
        json_file_path = ai_analysis_dir / filename
        
        logger.info(f"목 데이터 로드 시도: {json_file_path}")
        
        # 디렉토리가 존재하는지 확인
        if not ai_analysis_dir.exists():
            ai_analysis_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"목 데이터 디렉토리 생성됨: {ai_analysis_dir}")
        
        # JSON 파일이 존재하는지 확인
        if not json_file_path.exists():
            logger.warning(f"목 데이터 파일을 찾을 수 없음: {json_file_path}")
            
            # 파일이 없으면 기본 데이터 생성 후 저장
            fallback_data = generate_fallback_data()
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(fallback_data, f, ensure_ascii=False, indent=2)
            logger.info(f"기본 목 데이터 파일 생성됨: {json_file_path}")
            return fallback_data
        
        # JSON 파일 로드
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"목 데이터 로드 성공: {json_file_path}")
        return data
        
    except Exception as e:
        logger.error(f"목 데이터 로드 중 오류 발생: {str(e)}")
        return {}

def load_mock_ai_analysis() -> Dict[str, Any]:
    """
    AI 분석 목 데이터 로드
    
    Returns:
        Dict[str, Any]: 로드된 목 데이터
    """
    try:
        # load_mock_data 함수를 사용하여 목 데이터 로드
        data = load_mock_data("coffee_shop_with_ai_insights.json")
        if not data:
            return generate_fallback_data()
        
        # 결과 페이지에 필요한 구조로 변환
        result_data = {
            "url": data["website"]["url"],
            "title": data["website"]["name"],
            "description": data["website"]["description"],
            "created_at": "2025-05-06T20:52:46.403529",
            "tabs": ["기획서", "디자인", "아이디어"],
            "nav_items": generate_nav_items_from_pages(data.get("page_structure", [])),
            "components": generate_components_list(data),
            "colors": generate_colors_list(data),
            "layout_type": data.get("design_analysis", {}).get("layout", "반응형 그리드 레이아웃"),
            "design_insights": data.get("ai_analysis", {}).get("design_insights", ""),
            "functional_insights": data.get("ai_analysis", {}).get("functional_insights", ""),
            "recommendations": data.get("ai_analysis", {}).get("recommendations", ""),
            "tech_stack": data.get("tech_stack", []),
            "page_structure": data.get("page_structure", []),
            "overview": data.get("overview", ""),
            "mockups": {
                "homepage": "", # 실제 목업 이미지 경로
                "services": ""  # 실제 목업 이미지 경로
            },
            "accessibility_analysis": generate_accessibility_analysis(data)
        }
        
        return result_data
    
    except Exception as e:
        logger.error(f"목 데이터 변환 중 오류 발생: {str(e)}")
        return generate_fallback_data()

def generate_nav_items_from_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    페이지 구조에서 내비게이션 항목 생성
    
    Args:
        pages: 페이지 구조 리스트
        
    Returns:
        List[Dict[str, Any]]: 내비게이션 항목 리스트
    """
    nav_items = []
    
    # 기본 홈 항목 추가
    nav_items.append({"title": "홈", "url": "/", "has_submenu": False})
    
    # 페이지 항목 추가
    for page in pages:
        nav_items.append({
            "title": page.get("name", "페이지"),
            "url": f"/{page.get('name', '').lower().replace(' ', '-')}",
            "has_submenu": False
        })
    
    return nav_items

def generate_components_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    컴포넌트 목록 생성
    
    Args:
        data: 분석 데이터
        
    Returns:
        List[Dict[str, Any]]: 컴포넌트 목록
    """
    components = []
    
    # 페이지에서 컴포넌트 추출
    for page in data.get("page_structure", []):
        for component in page.get("components", []):
            components.append({
                "type": component,
                "description": f"{page.get('name', '페이지')}의 구성 요소"
            })
    
    return components

def generate_colors_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    색상 목록 생성
    
    Args:
        data: 분석 데이터
        
    Returns:
        List[Dict[str, Any]]: 색상 목록
    """
    colors = []
    
    # 디자인 분석에서 색상 추출
    for color in data.get("design_analysis", {}).get("color_palette", []):
        colors.append({
            "hex": color,
            "description": ""
        })
    
    return colors

def generate_accessibility_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    접근성 분석 정보 생성
    
    Args:
        data: 분석 데이터
        
    Returns:
        Dict[str, Any]: 접근성 분석 정보
    """
    # 데이터에서 접근성 관련 정보 추출 시도
    if data.get("accessibility_analysis"):
        return data.get("accessibility_analysis")
    
    # 추천 사항에서 접근성 관련 키워드 찾아 이슈 식별
    recommendations = data.get("ai_analysis", {}).get("recommendations", "")
    design_insights = data.get("ai_analysis", {}).get("design_insights", "")
    
    issues = []
    suggestions = []
    
    # 추천 사항에서 접근성 관련 항목 추출
    if "접근성" in recommendations or "accessibility" in recommendations.lower():
        # 기본 접근성 이슈 추가
        issues.append("접근성 개선이 권장됨")
        
        # 디자인 인사이트에서 색상 대비 문제 확인
        if "색상 대비" in design_insights or "contrast" in design_insights.lower():
            issues.append("색상 대비가 충분하지 않을 수 있음")
            suggestions.append("주요 색상 쌍의 대비를 WCAG AA 기준(4.5:1)으로 강화")
    
    # 기본 접근성 제안 항목
    if not suggestions:
        suggestions = [
            "모든 이미지에 적절한 alt 속성 추가",
            "버튼 및 링크에 aria-label 추가",
            "시맨틱 HTML5 요소 사용 (nav, main, section, article 등)",
            "키보드 초점 표시기 개선"
        ]
    
    # 기본 접근성 이슈 항목
    if not issues:
        issues = [
            "이미지에 대체 텍스트 누락 가능성",
            "키보드로 접근 불가능한 기능 존재 가능성",
            "ARIA 레이블 미사용 가능성"
        ]
    
    # 색상 정보 기반 대비 점검
    colors = data.get("design_analysis", {}).get("color_palette", [])
    if len(colors) >= 2:
        issues.append(f"색상 쌍의 대비 점검 필요 ({colors[0]}와 {colors[1]} 사이)")
    
    # 접근성 점수 및 레벨 설정 (기본값)
    score = 65  # 65% 준수율
    level = "부분 준수"
    
    return {
        "score": score,
        "level": level,
        "issues": issues,
        "suggestions": suggestions
    }

def generate_fallback_data() -> Dict[str, Any]:
    """
    폴백 데이터 생성 (데이터 로드 실패 시)
    
    Returns:
        Dict[str, Any]: 기본 데이터
    """
    return {
        "url": "https://coffeebeans.co.kr",
        "title": "커피빈스",
        "description": "프리미엄 커피와 티 전문점",
        "created_at": "2025-05-06T12:34:56",
        "tabs": ["기획서", "디자인", "아이디어"],
        "nav_items": [
            {"title": "홈", "url": "/", "has_submenu": False},
            {"title": "메뉴", "url": "/menu", "has_submenu": True},
            {"title": "매장찾기", "url": "/stores", "has_submenu": False},
            {"title": "이벤트", "url": "/events", "has_submenu": False}
        ],
        "components": [
            {"type": "내비게이션", "description": "상단 고정 메뉴바, 모바일 햄버거 메뉴"},
            {"type": "버튼", "description": "기본, 강조, 아웃라인 스타일"},
            {"type": "카드", "description": "그림자 효과가 있는 컨텐츠 카드"},
            {"type": "폼", "description": "라벨 상단 배치, 실시간 유효성 검사"}
        ],
        "colors": [
            {"hex": "#4B2C20", "description": "주요 브랜드 색상"},
            {"hex": "#FFC107", "description": "강조 색상"},
            {"hex": "#8D6E63", "description": "보조 색상"},
            {"hex": "#FFFFFF", "description": "배경 색상"},
            {"hex": "#212121", "description": "텍스트 색상"}
        ],
        "layout_type": "반응형 그리드 레이아웃",
        "design_insights": "색상 팔레트는 브랜드 정체성을 잘 반영하고 있으나 일부 텍스트와 배경 색상 조합에서 접근성 문제가 있을 수 있습니다.",
        "functional_insights": "검색 기능 강화 및 필터링 옵션 추가를 권장합니다.",
        "recommendations": "접근성 개선, 모바일 최적화, 성능 최적화, SEO 개선이 필요합니다.",
        "tech_stack": [
            "Frontend: React.js, Next.js",
            "Styling: Tailwind CSS",
            "Backend: Node.js, Express",
            "Database: MongoDB"
        ],
        "page_structure": [
            {
                "name": "메인 페이지",
                "description": "브랜드 소개 및 주요 메뉴, 프로모션 슬라이더를 포함",
                "components": ["히어로 섹션", "신제품 슬라이더", "카테고리 바로가기"]
            },
            {
                "name": "메뉴 페이지",
                "description": "전체 메뉴 카탈로그",
                "components": ["카테고리 필터", "메뉴 그리드", "상세 정보 모달"]
            }
        ],
        "overview": "커피빈스는 고품질 원두와 다양한 음료를 제공하는 커피 브랜드입니다.",
        "accessibility_analysis": {
            "score": 65,
            "level": "부분 준수",
            "issues": [
                "색상 대비가 충분하지 않음 (#4B2C20와 #8D6E63 사이)",
                "일부 이미지에 대체 텍스트 누락",
                "키보드로 접근 불가능한 기능 존재",
                "ARIA 레이블 미사용"
            ],
            "suggestions": [
                "주요 색상 쌍의 대비를 WCAG AA 기준(4.5:1)으로 강화",
                "모든 이미지에 적절한 alt 속성 추가",
                "버튼 및 링크에 aria-label 추가",
                "시맨틱 HTML5 요소 사용 강화 (nav, main, section, article 등)",
                "키보드 초점 표시기 개선"
            ]
        },
        "mockups": {
            "homepage": "",
            "services": ""
        }
    } 