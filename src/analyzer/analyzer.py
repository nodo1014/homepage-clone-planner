"""
웹사이트 콘텐츠 분석

이 모듈은 웹사이트 콘텐츠를 분석하여 메뉴 구조, 색상 팔레트, 레이아웃 등을 추출합니다.
"""
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json
import asyncio
from pathlib import Path
import os
import colorsys

# 내부 모듈 임포트
from src.analyzer.fetcher import WebsiteFetcher, fetch_website_content

# 로깅 설정
logger = logging.getLogger(__name__)

class WebsiteAnalyzer:
    """웹사이트 콘텐츠 분석 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        웹사이트 콘텐츠 분석 클래스 초기화
        
        Args:
            config (Dict[str, Any], optional): 설정 정보
        """
        self.config = config or {}
        self.timeout = self.config.get("analysis_timeout", 20)
        self.fetcher = WebsiteFetcher(timeout=self.timeout)
        self.analyzed_data = {
            "metadata": {},
            "menu": [],
            "colors": [],
            "layout": {},
            "components": [],
            "pages": [],
            "content_structure": {}
        }
    
    async def analyze_website(self, url: str) -> Tuple[bool, Dict[str, Any]]:
        """
        웹사이트 분석 시작
        
        Args:
            url (str): 분석할 웹사이트 URL
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (성공 여부, 분석 결과 또는 오류 메시지)
        """
        # URL 유효성 검증
        is_valid, url_or_error = self.fetcher.validate_url(url)
        if not is_valid:
            return False, {"error": url_or_error}
        
        # 실제 URL 설정
        url = url_or_error
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        try:
            # 웹사이트 콘텐츠 가져오기
            success, content = self.fetcher.fetch_content(url)
            if not success:
                return False, {"error": content}
            
            # 메타데이터 추출
            self.analyzed_data["metadata"] = self.fetcher.extract_metadata(content)
            
            # 메뉴 구조 추출
            self.analyzed_data["menu"] = self._extract_menu_structure(content, base_url)
            
            # 색상 팔레트 추출
            self.analyzed_data["colors"] = self._extract_color_palette(content)
            
            # 레이아웃 구조 분석
            self.analyzed_data["layout"] = self._analyze_layout(content)
            
            # UI 컴포넌트 분석
            self.analyzed_data["components"] = self._identify_ui_components(content)
            
            # 페이지 구조 분석
            self.analyzed_data["content_structure"] = self._analyze_content_structure(content)
            
            # 페이지 목록 가져오기 (메인 페이지만 포함)
            self.analyzed_data["pages"] = [{"url": url, "title": self.analyzed_data["metadata"]["title"]}]
            
            # 분석 결과 반환
            return True, self.analyzed_data
            
        except Exception as e:
            logger.error(f"웹사이트 분석 실패: {str(e)}")
            return False, {"error": f"웹사이트 분석 중 오류가 발생했습니다: {str(e)}"}
    
    def _extract_menu_structure(self, content: str, base_url: str) -> List[Dict[str, Any]]:
        """
        메뉴 구조 추출
        
        Args:
            content (str): 웹사이트 콘텐츠
            base_url (str): 기본 URL
            
        Returns:
            List[Dict[str, Any]]: 메뉴 구조
        """
        menu_items = []
        soup = BeautifulSoup(content, 'lxml')
        
        # 일반적인 메뉴 패턴 탐색
        menu_candidates = [
            soup.find('nav'),
            soup.find('header nav'),  # 헤더 내 네비게이션은 주요 메뉴일 가능성이 높음
            soup.find('div', {'id': re.compile(r'menu|navigation|nav|header', re.I)}),
            soup.find('ul', {'id': re.compile(r'menu|navigation|nav|header', re.I)}),
            soup.find('div', {'class': re.compile(r'menu|navigation|nav|gnb|main-menu|top-menu', re.I)}),
            soup.find('ul', {'class': re.compile(r'menu|navigation|nav|gnb|main-menu|top-menu', re.I)})
        ]
        
        # 최적의 메뉴 요소 선택
        menu_element = None
        max_links = 0
        
        for candidate in menu_candidates:
            if candidate:
                links = candidate.find_all('a')
                if len(links) > max_links:
                    menu_element = candidate
                    max_links = len(links)
        
        # 메뉴 요소가 없으면 빈 목록 반환
        if not menu_element:
            return menu_items
        
        # 재귀적으로 메뉴 구조 추출
        menu_items = self._extract_menu_recursive(menu_element, base_url)
        
        return menu_items
    
    def _extract_menu_recursive(self, element, base_url: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        재귀적으로 메뉴와 서브메뉴 추출
        
        Args:
            element: BeautifulSoup 요소
            base_url (str): 기본 URL
            depth (int): 현재 메뉴 깊이
            
        Returns:
            List[Dict[str, Any]]: 메뉴 구조
        """
        items = []
        
        # 메뉴 항목이 li 태그 내부에 있는 경우 (가장 일반적인 구조)
        if element.name == 'ul':
            for li in element.find_all('li', recursive=False):
                # 항목 추출
                item = self._extract_menu_item(li, base_url, depth)
                if item:
                    items.append(item)
        # div나 nav 같은 컨테이너인 경우
        else:
            # a 태그 직접 추출
            for a_tag in element.find_all('a', href=True, recursive=False):
                item = self._create_menu_item(a_tag, base_url, depth)
                if item:
                    items.append(item)
            
            # 내부 ul 태그가 있으면 재귀적으로 처리
            for ul in element.find_all('ul', recursive=False):
                sub_items = self._extract_menu_recursive(ul, base_url, depth)
                items.extend(sub_items)
        
        return items
    
    def _extract_menu_item(self, li_element, base_url: str, depth: int) -> Optional[Dict[str, Any]]:
        """
        li 요소에서 메뉴 항목과 서브메뉴 추출
        
        Args:
            li_element: li 태그 요소
            base_url (str): 기본 URL
            depth (int): 현재 메뉴 깊이
            
        Returns:
            Optional[Dict[str, Any]]: 메뉴 항목 또는 None
        """
        # a 태그 찾기
        a_tag = li_element.find('a', href=True)
        if not a_tag:
            return None
        
        # 기본 메뉴 항목 생성
        item = self._create_menu_item(a_tag, base_url, depth)
        if not item:
            return None
        
        # 서브메뉴 확인
        submenu = li_element.find('ul')
        if submenu:
            item["has_submenu"] = True
            item["children"] = self._extract_menu_recursive(submenu, base_url, depth + 1)
        else:
            item["has_submenu"] = False
            item["children"] = []
        
        return item
    
    def _create_menu_item(self, a_tag, base_url: str, depth: int) -> Optional[Dict[str, Any]]:
        """
        a 태그에서 메뉴 항목 생성
        
        Args:
            a_tag: a 태그 요소
            base_url (str): 기본 URL
            depth (int): 현재 메뉴 깊이
            
        Returns:
            Optional[Dict[str, Any]]: 메뉴 항목 또는 None
        """
        href = a_tag.get('href', '')
        text = a_tag.get_text().strip()
        
        # 빈 링크, 앵커, 자바스크립트 링크 건너뛰기
        if not href or href == '#' or href.startswith('javascript:'):
            # 모든 메뉴 항목을 포함하고 싶은 경우 앵커 링크도 허용
            # return None
            pass
        
        # 상대 경로를 절대 경로로 변환
        if not href.startswith(('http://', 'https://')):
            href = urljoin(base_url, href)
        
        # 메뉴 항목 생성
        return {
            "title": text,
            "url": href,
            "depth": depth,
            "has_submenu": False,  # 기본값, 나중에 업데이트됨
            "children": []  # 기본값, 나중에 업데이트됨
        }
    
    def _extract_color_palette(self, content: str) -> List[Dict[str, Any]]:
        """
        색상 팔레트 추출
        
        Args:
            content (str): 웹사이트 콘텐츠
            
        Returns:
            List[Dict[str, Any]]: 색상 팔레트
        """
        colors = []
        soup = BeautifulSoup(content, 'lxml')
        
        # CSS 스타일 태그에서 색상 추출
        for style in soup.find_all('style'):
            if style.string:
                # 색상 코드 추출 (HEX 및 RGB 형식)
                hex_colors = re.findall(r'#([0-9a-fA-F]{3,6})', style.string)
                rgb_colors = re.findall(r'rgb\((\d+,\s*\d+,\s*\d+)\)', style.string)
                rgba_colors = re.findall(r'rgba\((\d+,\s*\d+,\s*\d+,\s*[\d\.]+)\)', style.string)
                
                # HEX 색상 처리
                for hex_color in hex_colors:
                    # 3자리 HEX 코드를 6자리로 변환
                    if len(hex_color) == 3:
                        hex_color = ''.join([c*2 for c in hex_color])
                    
                    # 색상 정보 저장
                    colors.append({
                        "hex": f"#{hex_color}",
                        "rgb": self._hex_to_rgb(hex_color),
                        "type": self._categorize_color(hex_color)
                    })
                
                # RGB 색상 처리
                for rgb in rgb_colors:
                    r, g, b = map(int, re.split(r',\s*', rgb))
                    hex_color = self._rgb_to_hex(r, g, b)
                    
                    colors.append({
                        "hex": hex_color,
                        "rgb": (r, g, b),
                        "type": self._categorize_color(hex_color[1:])
                    })
        
        # 인라인 스타일에서 색상 추출
        for tag in soup.find_all(style=True):
            style = tag['style']
            
            # 색상 속성 추출
            color_props = re.findall(r'(?:color|background|background-color|border-color):\s*([^;]+)', style)
            
            for prop in color_props:
                # HEX 색상 확인
                hex_match = re.search(r'#([0-9a-fA-F]{3,6})', prop)
                if hex_match:
                    hex_color = hex_match.group(1)
                    
                    # 3자리 HEX 코드를 6자리로 변환
                    if len(hex_color) == 3:
                        hex_color = ''.join([c*2 for c in hex_color])
                    
                    # 색상 정보 저장
                    colors.append({
                        "hex": f"#{hex_color}",
                        "rgb": self._hex_to_rgb(hex_color),
                        "type": self._categorize_color(hex_color)
                    })
                
                # RGB 색상 확인
                rgb_match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', prop)
                if rgb_match:
                    r, g, b = map(int, rgb_match.groups())
                    hex_color = self._rgb_to_hex(r, g, b)
                    
                    colors.append({
                        "hex": hex_color,
                        "rgb": (r, g, b),
                        "type": self._categorize_color(hex_color[1:])
                    })
        
        # 중복 제거 및 빈도 기준 정렬
        unique_colors = {}
        for color in colors:
            hex_code = color["hex"].lower()
            if hex_code in unique_colors:
                unique_colors[hex_code]["count"] += 1
            else:
                unique_colors[hex_code] = color
                unique_colors[hex_code]["count"] = 1
        
        # 빈도 기준 내림차순 정렬
        sorted_colors = sorted(unique_colors.values(), key=lambda x: x["count"], reverse=True)
        
        # 상위 10개 색상만 반환
        return sorted_colors[:10]
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """
        HEX 색상 코드를 RGB로 변환
        
        Args:
            hex_color (str): HEX 색상 코드 (# 제외)
            
        Returns:
            Tuple[int, int, int]: RGB 색상 값
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """
        RGB 색상 값을 HEX 코드로 변환
        
        Args:
            r (int): 빨간색 값 (0-255)
            g (int): 녹색 값 (0-255)
            b (int): 파란색 값 (0-255)
            
        Returns:
            str: HEX 색상 코드 (# 포함)
        """
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _categorize_color(self, hex_color: str) -> str:
        """
        색상 분류 (primary, secondary, background, text 등)
        
        Args:
            hex_color (str): HEX 색상 코드 (# 제외)
            
        Returns:
            str: 색상 유형
        """
        r, g, b = self._hex_to_rgb(hex_color)
        # RGB를 HSV로 변환
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        
        # 밝기에 따른 분류
        if v < 0.2:
            return "dark"
        elif v > 0.8:
            return "light"
        
        # 채도에 따른 분류
        if s < 0.2:
            return "neutral"
        
        # 색상에 따른 분류
        if 0 <= h < 0.05 or h >= 0.95:
            return "red"
        elif 0.05 <= h < 0.11:
            return "orange"
        elif 0.11 <= h < 0.191:
            return "yellow"
        elif 0.191 <= h < 0.37:
            return "green"
        elif 0.37 <= h < 0.55:
            return "cyan"
        elif 0.55 <= h < 0.75:
            return "blue"
        elif 0.75 <= h < 0.83:
            return "purple"
        else:
            return "magenta"
    
    def _analyze_layout(self, content: str) -> Dict[str, Any]:
        """
        레이아웃 구조 분석
        
        Args:
            content (str): 웹사이트 콘텐츠
            
        Returns:
            Dict[str, Any]: 레이아웃 구조 정보
        """
        layout = {
            "header": False,
            "footer": False,
            "sidebar": False,
            "columns": 1,
            "width": "responsive",
            "content_sections": 0
        }
        
        soup = BeautifulSoup(content, 'lxml')
        
        # 헤더 확인
        header_candidates = [
            soup.find('header'),
            soup.find('div', {'id': re.compile(r'header', re.I)}),
            soup.find('div', {'class': re.compile(r'header', re.I)})
        ]
        layout["header"] = any(header_candidates)
        
        # 푸터 확인
        footer_candidates = [
            soup.find('footer'),
            soup.find('div', {'id': re.compile(r'footer', re.I)}),
            soup.find('div', {'class': re.compile(r'footer', re.I)})
        ]
        layout["footer"] = any(footer_candidates)
        
        # 사이드바 확인
        sidebar_candidates = [
            soup.find('aside'),
            soup.find('div', {'id': re.compile(r'sidebar|side', re.I)}),
            soup.find('div', {'class': re.compile(r'sidebar|side', re.I)})
        ]
        layout["sidebar"] = any(sidebar_candidates)
        
        # 컬럼 구조 확인
        main_content = soup.find('main') or soup.find('div', {'id': 'content'}) or soup.find('div', {'class': 'content'})
        if main_content:
            # 자식 요소 중 div나 section의 개수 확인
            column_candidates = main_content.find_all(['div', 'section'], recursive=False)
            if len(column_candidates) > 1:
                layout["columns"] = min(len(column_candidates), 4)  # 최대 4열로 제한
        
        # 컨텐츠 섹션 개수 확인
        sections = soup.find_all('section') + soup.find_all('div', {'class': re.compile(r'section|block', re.I)})
        layout["content_sections"] = len(sections)
        
        # 반응형 여부 확인 (viewport 메타태그)
        viewport_meta = soup.find('meta', {'name': 'viewport'})
        if viewport_meta:
            content = viewport_meta.get('content', '')
            if 'width=device-width' in content:
                layout["width"] = "responsive"
            else:
                layout["width"] = "fixed"
        else:
            layout["width"] = "fixed"
        
        return layout
    
    def _identify_ui_components(self, content: str) -> List[Dict[str, Any]]:
        """
        UI 컴포넌트 식별
        
        Args:
            content (str): 웹사이트 콘텐츠
            
        Returns:
            List[Dict[str, Any]]: 식별된 UI 컴포넌트 목록
        """
        components = []
        soup = BeautifulSoup(content, 'lxml')
        
        # 버튼 컴포넌트 찾기
        buttons = []
        buttons.extend(soup.find_all('button'))
        buttons.extend(soup.find_all('a', {'class': re.compile(r'btn|button', re.I)}))
        buttons.extend(soup.find_all('div', {'class': re.compile(r'btn|button', re.I)}))
        
        if buttons:
            components.append({
                "type": "button",
                "count": len(buttons),
                "variants": min(3, len(set([b.get('class', [''])[0] if b.get('class') else '' for b in buttons])))
            })
        
        # 폼 컴포넌트 찾기
        forms = soup.find_all('form')
        if forms:
            for form in forms:
                inputs = form.find_all(['input', 'textarea', 'select'])
                if inputs:
                    input_types = [i.get('type', 'text') if i.name == 'input' else i.name for i in inputs]
                    components.append({
                        "type": "form",
                        "fields": len(inputs),
                        "input_types": list(set(input_types))
                    })
        
        # 카드 컴포넌트 찾기
        card_candidates = soup.find_all(['div', 'article'], {'class': re.compile(r'card|box|item', re.I)})
        if card_candidates:
            components.append({
                "type": "card",
                "count": len(card_candidates)
            })
        
        # 이미지 슬라이더/캐러셀 찾기
        slider_candidates = [
            soup.find('div', {'class': re.compile(r'slider|carousel|slideshow', re.I)}),
            soup.find('div', {'id': re.compile(r'slider|carousel|slideshow', re.I)})
        ]
        if any(slider_candidates):
            components.append({
                "type": "slider",
                "count": 1
            })
        
        # 네비게이션 컴포넌트 찾기
        if soup.find('nav'):
            components.append({
                "type": "navigation",
                "count": len(soup.find_all('nav'))
            })
        
        return components
    
    def _analyze_content_structure(self, content: str) -> Dict[str, Any]:
        """
        컨텐츠 구조 분석
        
        Args:
            content (str): 웹사이트 콘텐츠
            
        Returns:
            Dict[str, Any]: 컨텐츠 구조 정보
        """
        structure = {
            "headings": {},
            "paragraphs": 0,
            "images": 0,
            "links": 0,
            "lists": 0,
            "tables": 0,
            "forms": 0
        }
        
        soup = BeautifulSoup(content, 'lxml')
        
        # 제목 태그 분석
        for i in range(1, 7):
            heading_count = len(soup.find_all(f'h{i}'))
            if heading_count > 0:
                structure["headings"][f"h{i}"] = heading_count
        
        # 문단 개수
        structure["paragraphs"] = len(soup.find_all('p'))
        
        # 이미지 개수
        structure["images"] = len(soup.find_all('img'))
        
        # 링크 개수
        structure["links"] = len(soup.find_all('a', href=True))
        
        # 목록 개수
        structure["lists"] = len(soup.find_all(['ul', 'ol']))
        
        # 테이블 개수
        structure["tables"] = len(soup.find_all('table'))
        
        # 폼 개수
        structure["forms"] = len(soup.find_all('form'))
        
        return structure

# 편의 함수
async def analyze_website(url: str, config: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    웹사이트 분석 편의 함수
    
    Args:
        url (str): 분석할 웹사이트 URL
        config (Dict[str, Any], optional): 설정 정보
        
    Returns:
        Tuple[bool, Dict[str, Any]]: (성공 여부, 분석 결과 또는 오류 메시지)
    """
    analyzer = WebsiteAnalyzer(config)
    return await analyzer.analyze_website(url) 