"""
마크다운 기획서 생성

이 모듈은 분석 결과를 마크다운 형식의 기획서로 변환하는 기능을 제공합니다.
"""
import logging
from typing import Dict, Any, List, Tuple, Optional
import json
from pathlib import Path
import os
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

class MarkdownGenerator:
    """마크다운 기획서 생성 클래스"""
    
    def __init__(self, output_dir: str = None):
        """
        마크다운 기획서 생성 클래스 초기화
        
        Args:
            output_dir (str, optional): 결과물 저장 디렉토리
        """
        self.output_dir = output_dir or "./output"
        
        # 출력 디렉토리 생성
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_planning_doc(self, url: str, analysis_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        기획서 생성
        
        Args:
            url (str): 분석한 웹사이트 URL
            analysis_data (Dict[str, Any]): 분석 결과
            
        Returns:
            Tuple[bool, str]: (성공 여부, 기획서 경로 또는 오류 메시지)
        """
        try:
            # 기획서 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain = url.replace("https://", "").replace("http://", "").split("/")[0]
            filename = f"planning_{domain}_{timestamp}.md"
            file_path = os.path.join(self.output_dir, filename)
            
            # 기획서 내용 생성
            content = self._create_planning_content(url, analysis_data)
            
            # 파일로 저장
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return True, file_path
        
        except Exception as e:
            logger.error(f"기획서 생성 실패: {str(e)}")
            return False, f"기획서 생성 중 오류가 발생했습니다: {str(e)}"
    
    def _create_planning_content(self, url: str, data: Dict[str, Any]) -> str:
        """
        기획서 내용 생성
        
        Args:
            url (str): 분석한 웹사이트 URL
            data (Dict[str, Any]): 분석 결과
            
        Returns:
            str: 마크다운 형식의 기획서 내용
        """
        metadata = data.get("metadata", {})
        menu = data.get("menu", [])
        colors = data.get("colors", [])
        layout = data.get("layout", {})
        components = data.get("components", [])
        content_structure = data.get("content_structure", {})
        
        # 기획서 제목
        title = metadata.get("title", "웹사이트")
        site_description = metadata.get("description", "")
        
        # 현재 날짜
        today = datetime.now().strftime("%Y년 %m월 %d일")
        
        # 마크다운 내용 시작
        content = f"""# {title} 클론 기획서

## 1. 프로젝트 개요

### 1.1 분석 대상
- **사이트명**: {title}
- **URL**: {url}
- **분석일**: {today}

### 1.2 사이트 설명
{site_description}

### 1.3 주요 특징
"""
        
        # 주요 특징 추가
        features = []
        if layout.get("header", False):
            features.append("상단 헤더 네비게이션")
        if layout.get("footer", False):
            features.append("하단 푸터 정보")
        if layout.get("sidebar", False):
            features.append("사이드바 메뉴")
        if layout.get("width") == "responsive":
            features.append("반응형 레이아웃")
        
        # UI 컴포넌트 기반 특징 추가
        for component in components:
            if component["type"] == "slider":
                features.append("이미지 슬라이더/캐러셀")
            elif component["type"] == "form" and component.get("fields", 0) > 3:
                features.append("다중 입력 폼")
            elif component["type"] == "card" and component.get("count", 0) > 3:
                features.append("카드 기반 콘텐츠 표시")
        
        # 특징이 없으면 기본 특징 추가
        if not features:
            features = ["심플한 디자인", "정보 중심 레이아웃"]
        
        # 특징 리스트 추가
        for feature in features:
            content += f"- {feature}\n"
        
        # 메뉴 구조 추가
        content += """
## 2. 사이트 구조

### 2.1 메뉴 구조
"""
        
        if menu:
            for item in menu:
                title = item.get("title", "메뉴 항목")
                url = item.get("url", "#")
                has_submenu = item.get("has_submenu", False)
                
                # 서브메뉴 표시
                submenu_indicator = " (하위 메뉴 있음)" if has_submenu else ""
                content += f"- {title}{submenu_indicator}\n"
        else:
            content += "- 메뉴 구조를 식별할 수 없습니다.\n"
        
        # 페이지 구성 추가
        content += """
### 2.2 주요 페이지 구성
- **홈페이지**: 메인 콘텐츠, 주요 소개
"""
        
        # 메뉴에서 주요 페이지 추출
        if menu and len(menu) > 0:
            main_pages = menu[:min(4, len(menu))]
            for page in main_pages:
                title = page.get("title", "페이지")
                content += f"- **{title}**: {title} 관련 콘텐츠\n"
        
        # 레이아웃 분석 추가
        content += f"""
## 3. 디자인 분석

### 3.1 레이아웃 구조
- **헤더**: {'있음' if layout.get('header', False) else '없음'}
- **푸터**: {'있음' if layout.get('footer', False) else '없음'}
- **사이드바**: {'있음' if layout.get('sidebar', False) else '없음'}
- **컬럼 구조**: {layout.get('columns', 1)}열 구조
- **반응형**: {'지원' if layout.get('width') == 'responsive' else '미지원'}
- **콘텐츠 섹션**: {layout.get('content_sections', 0)}개

### 3.2 색상 팔레트
"""
        
        # 색상 팔레트 추가
        if colors:
            for i, color in enumerate(colors[:5]):
                hex_code = color.get("hex", "#000000")
                color_type = color.get("type", "기타")
                content += f"- **색상 {i+1}**: {hex_code} ({color_type})\n"
        else:
            content += "- 색상 정보를 추출할 수 없습니다.\n"
        
        # UI 컴포넌트 추가
        content += """
### 3.3 UI 컴포넌트
"""
        
        if components:
            for component in components:
                comp_type = component.get("type", "unknown")
                count = component.get("count", 0)
                
                if comp_type == "button":
                    variants = component.get("variants", 1)
                    content += f"- **버튼**: {count}개 (변형 {variants}개)\n"
                elif comp_type == "form":
                    fields = component.get("fields", 0)
                    input_types = component.get("input_types", [])
                    content += f"- **폼**: {fields}개 필드 ({', '.join(input_types)})\n"
                elif comp_type == "card":
                    content += f"- **카드**: {count}개\n"
                elif comp_type == "slider":
                    content += f"- **슬라이더/캐러셀**: {count}개\n"
                elif comp_type == "navigation":
                    content += f"- **네비게이션**: {count}개\n"
        else:
            content += "- UI 컴포넌트를 식별할 수 없습니다.\n"
        
        # 콘텐츠 구조 추가
        content += """
### 3.4 콘텐츠 구조
"""
        
        # 헤딩 구조
        headings = content_structure.get("headings", {})
        if headings:
            content += "- **헤딩 구조**:\n"
            for h_level, count in headings.items():
                content += f"  - {h_level}: {count}개\n"
        
        # 기타 콘텐츠 요소
        paragraphs = content_structure.get("paragraphs", 0)
        images = content_structure.get("images", 0)
        links = content_structure.get("links", 0)
        lists = content_structure.get("lists", 0)
        tables = content_structure.get("tables", 0)
        
        content += f"""- **문단**: {paragraphs}개
- **이미지**: {images}개
- **링크**: {links}개
- **목록**: {lists}개
- **테이블**: {tables}개

## 4. 개발 가이드

### 4.1 기술 스택 추천
- **프론트엔드**: HTML5, CSS3, JavaScript (또는 React, Vue.js)
- **CSS 프레임워크**: {'Bootstrap 또는 Tailwind CSS' if layout.get('width') == 'responsive' else 'Custom CSS'}
- **반응형 지원**: {'필요' if layout.get('width') == 'responsive' else '선택적'}
- **이미지 최적화**: {'WebP 포맷 권장 (다수의 이미지 사용)' if images > 10 else '표준 이미지 포맷 사용 가능'}

### 4.2 개발 우선순위
1. 기본 레이아웃 및 반응형 구조 구현
2. 메인 페이지 디자인 및 컴포넌트 개발
3. 메뉴 및 네비게이션 구현
"""

        # 특정 컴포넌트가 있는 경우 우선순위 추가
        for component in components:
            if component["type"] == "slider" and component.get("count", 0) > 0:
                content += "4. 이미지 슬라이더/캐러셀 구현\n"
                break
        
        # 개발 난이도 평가
        difficulty = "중간"
        if layout.get("width") == "responsive" and images > 10 and len(components) > 3:
            difficulty = "높음"
        elif layout.get("sidebar", False) == False and images < 5 and len(components) < 3:
            difficulty = "낮음"
        
        content += f"""
### 4.3 개발 난이도 평가
- **전체 난이도**: {difficulty}
- **예상 개발 기간**: {'2-3주' if difficulty == '높음' else '1-2주' if difficulty == '중간' else '3-5일'}
- **주의사항**: {'반응형 레이아웃 및 다양한 UI 컴포넌트 구현 필요' if difficulty == '높음' else '기본적인 레이아웃 및 콘텐츠 구현 중심' if difficulty == '낮음' else '일반적인 웹사이트 개발 수준'}

## 5. 부록

### 5.1 참고 자료
- 원본 사이트: {url}
- 분석일: {today}

### 5.2 비고
- 이 기획서는 자동 분석을 통해 생성되었으며, 실제 개발 시 세부 조정이 필요할 수 있습니다.
- 웹사이트의 상세 기능 및 비즈니스 로직은 직접 확인이 필요합니다.
"""
        
        return content

# 편의 함수
def generate_markdown_planning(url: str, analysis_data: Dict[str, Any], output_dir: str = None) -> Tuple[bool, str]:
    """
    마크다운 기획서 생성 편의 함수
    
    Args:
        url (str): 분석한 웹사이트 URL
        analysis_data (Dict[str, Any]): 분석 결과
        output_dir (str, optional): 결과물 저장 디렉토리
        
    Returns:
        Tuple[bool, str]: (성공 여부, 기획서 경로 또는 오류 메시지)
    """
    generator = MarkdownGenerator(output_dir=output_dir)
    return generator.generate_planning_doc(url, analysis_data) 