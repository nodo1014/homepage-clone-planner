"""
AI 친화형 웹사이트 분석 예제

이 모듈은 웹사이트 분석 결과를 AI가 쉽게 이해할 수 있는 형식으로 변환하고 활용하는 예제를 제공합니다.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

class AIAnalysisManager:
    """AI 친화형 웹사이트 분석 관리 클래스"""
    
    def __init__(self, output_dir: str = None):
        """
        AI 친화형 웹사이트 분석 관리 클래스 초기화
        
        Args:
            output_dir (str, optional): 출력 디렉토리 경로
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "outputs"
        
    def create_ai_structure(self, task_id: str, analysis_data: Dict[str, Any]) -> str:
        """
        AI 친화형 구조 메타데이터 생성
        
        Args:
            task_id (str): 작업 ID
            analysis_data (Dict[str, Any]): 웹사이트 분석 결과 데이터
            
        Returns:
            str: 생성된 메타데이터 파일 경로
        """
        # 메타데이터 디렉토리 생성
        meta_dir = self.output_dir / task_id / "meta"
        os.makedirs(meta_dir, exist_ok=True)
        
        # 기본 메타데이터 구성
        url = analysis_data.get("url", "")
        metadata = analysis_data.get("metadata", {})
        
        # UI 구조 JSON 파일 생성
        ui_structure = {
            "url": url,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "keywords": metadata.get("keywords", []),
            "pages": [],
            "nav": [],
            "components": analysis_data.get("components", []),
            "layout": analysis_data.get("layout", {})
        }
        
        # 메뉴 정보 추출
        menu_items = analysis_data.get("menu", [])
        for menu_item in menu_items:
            ui_structure["nav"].append({
                "title": menu_item.get("title", ""),
                "url": menu_item.get("url", ""),
                "has_submenu": menu_item.get("has_submenu", False),
                "children": self._process_menu_children(menu_item.get("children", []))
            })
        
        # 페이지 정보 추출
        pages = analysis_data.get("pages", [])
        for page in pages:
            ui_structure["pages"].append({
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                "purpose": self._infer_page_purpose(page.get("title", ""), page.get("url", ""))
            })
        
        # UI 구조 저장
        ui_structure_path = meta_dir / "ui-structure.json"
        with open(ui_structure_path, "w", encoding="utf-8") as f:
            json.dump(ui_structure, f, ensure_ascii=False, indent=2)
        
        # 디자인 요소 JSON 파일 생성
        design_data = {
            "colors": analysis_data.get("colors", []),
            "layout_type": analysis_data.get("layout", {}).get("type", "unknown"),
            "components": analysis_data.get("components", []),
            "style_patterns": self._infer_style_patterns(analysis_data)
        }
        
        # 디자인 요소 저장
        design_path = meta_dir / "design-elements.json"
        with open(design_path, "w", encoding="utf-8") as f:
            json.dump(design_data, f, ensure_ascii=False, indent=2)
        
        # 콘텐츠 구조 JSON 파일 생성
        content_structure = analysis_data.get("content_structure", {})
        content_path = meta_dir / "content-structure.json"
        with open(content_path, "w", encoding="utf-8") as f:
            json.dump(content_structure, f, ensure_ascii=False, indent=2)
        
        return str(ui_structure_path)
    
    def _process_menu_children(self, children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        메뉴 하위 항목 처리
        
        Args:
            children (List[Dict[str, Any]]): 메뉴 하위 항목 목록
            
        Returns:
            List[Dict[str, Any]]: 처리된 하위 항목 목록
        """
        result = []
        for child in children:
            result.append({
                "title": child.get("title", ""),
                "url": child.get("url", ""),
                "has_submenu": child.get("has_submenu", False),
                "children": self._process_menu_children(child.get("children", []))
            })
        return result
    
    def _infer_page_purpose(self, title: str, url: str) -> str:
        """
        페이지 목적 추론
        
        Args:
            title (str): 페이지 제목
            url (str): 페이지 URL
            
        Returns:
            str: 추론된 페이지 목적
        """
        # 간단한 키워드 기반 추론
        title_lower = title.lower()
        url_lower = url.lower()
        
        # 홈페이지
        if any(keyword in url_lower for keyword in ["index", "home", "main"]) or url_lower.endswith("/"):
            return "홈페이지"
        
        # 소개 페이지
        if any(keyword in title_lower or keyword in url_lower for keyword in ["about", "company", "소개", "회사", "about-us"]):
            return "소개 페이지"
        
        # 연락처 페이지
        if any(keyword in title_lower or keyword in url_lower for keyword in ["contact", "문의", "연락", "지원", "support"]):
            return "연락처/문의 페이지"
        
        # 제품/서비스 페이지
        if any(keyword in title_lower or keyword in url_lower for keyword in ["product", "service", "제품", "서비스"]):
            return "제품/서비스 페이지"
        
        # 로그인/회원가입 페이지
        if any(keyword in title_lower or keyword in url_lower for keyword in ["login", "register", "signup", "sign-up", "로그인", "회원가입"]):
            return "로그인/회원가입 페이지"
        
        # 기본값
        return "미확인"
    
    def _infer_style_patterns(self, analysis_data: Dict[str, Any]) -> List[str]:
        """
        디자인 스타일 패턴 추론
        
        Args:
            analysis_data (Dict[str, Any]): 웹사이트 분석 결과 데이터
            
        Returns:
            List[str]: 추론된 스타일 패턴 목록
        """
        patterns = []
        
        # 색상 분석
        colors = analysis_data.get("colors", [])
        if len(colors) <= 3:
            patterns.append("미니멀한 색상 구성")
        elif len(colors) >= 6:
            patterns.append("다채로운 색상 구성")
        
        # 레이아웃 분석
        layout = analysis_data.get("layout", {})
        layout_type = layout.get("type", "")
        
        if layout_type == "responsive":
            patterns.append("반응형 디자인")
        elif layout_type == "fixed":
            patterns.append("고정 너비 디자인")
        
        if layout.get("has_sidebar", False):
            patterns.append("사이드바 레이아웃")
        
        if layout.get("has_hero", False):
            patterns.append("히어로 섹션 포함")
        
        # 컴포넌트 분석
        components = analysis_data.get("components", [])
        component_types = [comp.get("type", "") for comp in components]
        
        if "card" in component_types:
            patterns.append("카드 기반 UI")
        
        if "slider" in component_types or "carousel" in component_types:
            patterns.append("슬라이더/캐러셀 활용")
        
        if "modal" in component_types:
            patterns.append("모달 다이얼로그 활용")
        
        if "tab" in component_types:
            patterns.append("탭 인터페이스 활용")
        
        return patterns
    
    def get_ai_structure(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        AI 친화형 구조 메타데이터 가져오기
        
        Args:
            task_id (str): 작업 ID
            
        Returns:
            Optional[Dict[str, Any]]: 메타데이터 또는 None
        """
        ui_structure_path = self.output_dir / task_id / "meta" / "ui-structure.json"
        
        if not ui_structure_path.exists():
            return None
        
        try:
            with open(ui_structure_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"UI 구조 파일 로드 실패: {str(e)}")
            return None

# 예제 사용
def create_example_structure():
    """
    예제 AI 친화형 구조 생성
    """
    # 분석 결과 예제
    analysis_data = {
        "url": "https://example.com",
        "metadata": {
            "title": "Example Website",
            "description": "This is an example website for demonstration",
            "keywords": ["example", "demo", "website"]
        },
        "menu": [
            {
                "title": "Home",
                "url": "https://example.com/",
                "has_submenu": False,
                "children": []
            },
            {
                "title": "Products",
                "url": "https://example.com/products",
                "has_submenu": True,
                "children": [
                    {
                        "title": "Product A",
                        "url": "https://example.com/products/a",
                        "has_submenu": False,
                        "children": []
                    },
                    {
                        "title": "Product B",
                        "url": "https://example.com/products/b",
                        "has_submenu": False,
                        "children": []
                    }
                ]
            },
            {
                "title": "About",
                "url": "https://example.com/about",
                "has_submenu": False,
                "children": []
            },
            {
                "title": "Contact",
                "url": "https://example.com/contact",
                "has_submenu": False,
                "children": []
            }
        ],
        "pages": [
            {"url": "https://example.com/", "title": "Example Home"},
            {"url": "https://example.com/products", "title": "Our Products"},
            {"url": "https://example.com/about", "title": "About Us"},
            {"url": "https://example.com/contact", "title": "Contact Us"}
        ],
        "colors": [
            {"hex": "#1a73e8", "name": "Blue", "type": "primary"},
            {"hex": "#ffffff", "name": "White", "type": "background"},
            {"hex": "#202124", "name": "Dark Gray", "type": "text"}
        ],
        "layout": {
            "type": "responsive",
            "has_sidebar": False,
            "has_hero": True,
            "columns": 12
        },
        "components": [
            {"type": "button", "count": 5},
            {"type": "card", "count": 3},
            {"type": "hero", "count": 1},
            {"type": "footer", "count": 1}
        ],
        "content_structure": {
            "header": {
                "has_logo": True,
                "has_nav": True
            },
            "main": {
                "sections": ["hero", "features", "testimonials"]
            },
            "footer": {
                "has_links": True,
                "has_social": True,
                "has_copyright": True
            }
        }
    }
    
    # AI 친화형 구조 생성
    manager = AIAnalysisManager()
    task_id = "example_task_123"
    result_path = manager.create_ai_structure(task_id, analysis_data)
    
    print(f"AI 친화형 구조 메타데이터 생성 완료: {result_path}")
    
    # 생성된 구조 읽기
    structure = manager.get_ai_structure(task_id)
    if structure:
        print(f"메타데이터 읽기 성공: {structure['title']}")
    else:
        print("메타데이터 읽기 실패")

if __name__ == "__main__":
    create_example_structure() 