"""
HTML 콘텐츠 추출 모듈

이 모듈은 웹 페이지에서 HTML 콘텐츠를 가져오고 분석하는 기능을 제공합니다.
"""
import logging
import requests
from typing import Tuple, Dict, List, Any, Optional
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, urlparse
import time
import random
from requests.exceptions import RequestException

# 로거 설정
logger = logging.getLogger(__name__)

class HTMLExtractor:
    """HTML 콘텐츠 추출 클래스"""
    
    def __init__(self, user_agent: str = None, timeout: int = 10, max_retries: int = 3):
        """
        HTML 추출기 초기화
        
        Args:
            user_agent: 사용할 User-Agent 문자열
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 기본 User-Agent 설정
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        # 기본 헤더 설정
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        logger.debug(f"HTMLExtractor 초기화: User-Agent={self.user_agent}")
    
    def fetch_html(self, url: str) -> Tuple[bool, Any]:
        """
        URL에서 HTML 콘텐츠 가져오기
        
        Args:
            url: 가져올 URL
            
        Returns:
            Tuple[bool, Any]: (성공 여부, HTML 콘텐츠 또는 오류 메시지)
        """
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                logger.info(f"URL 가져오기 시도: {url} (시도 {retry_count + 1}/{self.max_retries})")
                
                # 요청 전 약간의 지연 추가 (서버 부하 방지)
                if retry_count > 0:
                    time.sleep(random.uniform(1, 3))
                
                # GET 요청
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True  # 리다이렉트 자동 처리
                )
                
                # 상태 코드 확인
                if response.status_code == 200:
                    logger.debug(f"URL 가져오기 성공: {url}")
                    
                    # 리다이렉트 발생 시 최종 URL 로깅
                    if response.url != url:
                        logger.info(f"리다이렉트 발생: {url} -> {response.url}")
                    
                    # 인코딩 감지 (response.encoding은 때때로 부정확할 수 있음)
                    if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                        # HTML에서 인코딩 감지 시도
                        detected_encoding = self._detect_encoding(response.content)
                        if detected_encoding:
                            response.encoding = detected_encoding
                    
                    return True, response.text
                else:
                    logger.warning(f"HTTP 오류 {response.status_code}: {url}")
                    retry_count += 1
                    
                    # 서버 오류(5xx)인 경우에만 재시도
                    if not (500 <= response.status_code < 600):
                        return False, f"HTTP 오류 {response.status_code}"
            
            except RequestException as e:
                logger.error(f"URL 가져오기 실패: {url} - {str(e)}")
                retry_count += 1
                
                # 마지막 시도면 실패 반환
                if retry_count >= self.max_retries:
                    return False, f"요청 실패: {str(e)}"
        
        return False, "최대 재시도 횟수 초과"
    
    def _detect_encoding(self, content: bytes) -> Optional[str]:
        """
        HTML 콘텐츠에서 인코딩 감지
        
        Args:
            content: HTML 바이트 콘텐츠
            
        Returns:
            Optional[str]: 감지된 인코딩 또는 None
        """
        # <meta charset="..."> 패턴
        charset_pattern = re.compile(b'<meta[^>]*charset=["\']?([^"\'>]*)', re.IGNORECASE)
        charset_match = charset_pattern.search(content)
        
        if charset_match:
            charset = charset_match.group(1).decode('ascii', errors='ignore').strip()
            logger.debug(f"HTML에서 감지된 인코딩: {charset}")
            return charset
        
        # <meta http-equiv="Content-Type" content="text/html; charset=..."> 패턴
        charset_pattern2 = re.compile(b'<meta[^>]*http-equiv=["\']?Content-Type["\']?[^>]*content=["\']?[^;]*;\s*charset=([^"\'>]*)', re.IGNORECASE)
        charset_match2 = charset_pattern2.search(content)
        
        if charset_match2:
            charset = charset_match2.group(1).decode('ascii', errors='ignore').strip()
            logger.debug(f"Content-Type에서 감지된 인코딩: {charset}")
            return charset
        
        return None
    
    def extract_metadata(self, html: str, url: str) -> Dict[str, Any]:
        """
        HTML에서 메타데이터 추출
        
        Args:
            html: HTML 문자열
            url: 페이지 URL
            
        Returns:
            Dict[str, Any]: 추출된 메타데이터
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 기본 메타데이터 구조
        metadata = {
            "url": url,
            "title": None,
            "description": None,
            "keywords": [],
            "og_image": None,
            "lang": None,
            "meta_tags": {},
            "charset": None
        }
        
        # 제목 추출
        title_tag = soup.find('title')
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)
        
        # 언어 추출
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata["lang"] = html_tag.get('lang')
        
        # 메타 태그 추출
        for meta_tag in soup.find_all('meta'):
            # 메타 태그 속성을 딕셔너리로 변환
            attrs = {key.lower(): value for key, value in meta_tag.attrs.items()}
            
            # 문자 인코딩 추출
            if 'charset' in attrs:
                metadata["charset"] = attrs['charset']
            
            # 이름이 있는 메타 태그
            if 'name' in attrs and 'content' in attrs:
                name = attrs['name'].lower()
                content = attrs['content']
                
                metadata["meta_tags"][name] = content
                
                # 주요 메타 태그 별도 추출
                if name == 'description':
                    metadata["description"] = content
                elif name == 'keywords':
                    # 쉼표로 구분된 키워드 리스트로 변환
                    keywords = [k.strip() for k in content.split(',') if k.strip()]
                    metadata["keywords"] = keywords
            
            # Open Graph 태그
            if 'property' in attrs and attrs['property'].startswith('og:') and 'content' in attrs:
                og_property = attrs['property'][3:]  # 'og:' 접두사 제거
                content = attrs['content']
                
                # Open Graph 속성 추가
                if og_property == 'image':
                    # 상대 URL을 절대 URL로 변환
                    metadata["og_image"] = urljoin(url, content)
                
                # meta_tags에도 기록
                metadata["meta_tags"][f"og:{og_property}"] = content
        
        logger.debug(f"메타데이터 추출 완료: {url}")
        return metadata
    
    def extract_links(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """
        HTML에서 링크 추출
        
        Args:
            html: HTML 문자열
            base_url: 기본 URL (상대 링크를 절대 링크로 변환하는 데 사용)
            
        Returns:
            List[Dict[str, str]]: 추출된 링크 목록
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        # 링크 추출
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            
            # javascript:, mailto:, tel: 등의 링크 제외
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            # 빈 링크 제외
            if not href:
                continue
            
            # 상대 URL을 절대 URL로 변환
            abs_url = urljoin(base_url, href)
            
            # URL 정규화 (중복 슬래시 제거 등)
            parsed = urlparse(abs_url)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized_url += f"?{parsed.query}"
            if parsed.fragment:
                normalized_url += f"#{parsed.fragment}"
            
            # 링크 텍스트 추출
            link_text = a_tag.get_text(strip=True)
            
            # 링크 정보 추가
            links.append({
                "url": normalized_url,
                "text": link_text,
                "title": a_tag.get('title', ''),
                "is_internal": parsed.netloc == urlparse(base_url).netloc
            })
        
        logger.debug(f"링크 {len(links)}개 추출 완료: {base_url}")
        return links
    
    def extract_images(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """
        HTML에서 이미지 추출
        
        Args:
            html: HTML 문자열
            base_url: 기본 URL (상대 링크를 절대 링크로 변환하는 데 사용)
            
        Returns:
            List[Dict[str, str]]: 추출된 이미지 목록
        """
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        
        # 이미지 추출
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src', '').strip()
            
            # 빈 소스 제외
            if not src:
                continue
            
            # data: URI 제외
            if src.startswith('data:'):
                continue
            
            # 상대 URL을 절대 URL로 변환
            abs_url = urljoin(base_url, src)
            
            # 이미지 정보 추가
            images.append({
                "url": abs_url,
                "alt": img_tag.get('alt', ''),
                "title": img_tag.get('title', ''),
                "width": img_tag.get('width', ''),
                "height": img_tag.get('height', '')
            })
        
        logger.debug(f"이미지 {len(images)}개 추출 완료: {base_url}")
        return images
    
    def extract_structured_data(self, html: str) -> List[Dict[str, Any]]:
        """
        HTML에서 구조화된 데이터 추출 (JSON-LD)
        
        Args:
            html: HTML 문자열
            
        Returns:
            List[Dict[str, Any]]: 추출된 구조화된 데이터 목록
        """
        soup = BeautifulSoup(html, 'html.parser')
        structured_data = []
        
        # JSON-LD 형식의 구조화된 데이터 추출
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except (json.JSONDecodeError, TypeError):
                logger.warning("JSON-LD 파싱 실패")
        
        logger.debug(f"구조화된 데이터 {len(structured_data)}개 추출 완료")
        return structured_data
    
    def extract_text_content(self, html: str) -> str:
        """
        HTML에서 텍스트 콘텐츠만 추출
        
        Args:
            html: HTML 문자열
            
        Returns:
            str: 추출된 텍스트 콘텐츠
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 스크립트, 스타일, SVG 태그 제거
        for tag in soup.select('script, style, svg'):
            tag.extract()
        
        # 텍스트 추출 (여러 공백을 하나로 변환)
        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        
        logger.debug(f"텍스트 콘텐츠 추출 완료: {len(text)} 문자")
        return text
    
    def extract_html_structure(self, html: str) -> Dict[str, Any]:
        """
        HTML 구조 추출 (주요 섹션 및 요소)
        
        Args:
            html: HTML 문자열
            
        Returns:
            Dict[str, Any]: 추출된 HTML 구조
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 기본 구조 정보
        structure = {
            "has_header": bool(soup.find('header')),
            "has_footer": bool(soup.find('footer')),
            "has_nav": bool(soup.find('nav')),
            "has_sidebar": bool(soup.find(class_=lambda c: c and ('sidebar' in c.lower() or 'side-bar' in c.lower()))),
            "has_main": bool(soup.find('main')),
            "sections": []
        }
        
        # 섹션 추출
        section_tags = ['section', 'article', 'div']
        for tag_name in section_tags:
            for section in soup.find_all(tag_name, class_=lambda c: c and (
                'section' in c.lower() or
                'container' in c.lower() or
                'content' in c.lower() or
                'block' in c.lower()
            )):
                # 섹션 ID 또는 클래스 이름
                section_id = section.get('id', '')
                section_class = ' '.join(section.get('class', []))
                
                # 섹션 제목 (h1-h6 태그)
                heading = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                heading_text = heading.get_text(strip=True) if heading else ''
                
                # 섹션 정보 추가
                structure["sections"].append({
                    "tag": tag_name,
                    "id": section_id,
                    "class": section_class,
                    "heading": heading_text
                })
        
        logger.debug(f"HTML 구조 추출 완료: {len(structure['sections'])} 섹션")
        return structure

# 모듈 수준 함수
def fetch_page(url: str) -> Tuple[bool, Any]:
    """
    URL에서 페이지 가져오기
    
    Args:
        url: 가져올 URL
        
    Returns:
        Tuple[bool, Any]: (성공 여부, HTML 콘텐츠 또는 오류 메시지)
    """
    extractor = HTMLExtractor()
    return extractor.fetch_html(url)

def analyze_page(html: str, url: str) -> Dict[str, Any]:
    """
    HTML 페이지 분석
    
    Args:
        html: HTML 문자열
        url: 페이지 URL
        
    Returns:
        Dict[str, Any]: 분석 결과
    """
    extractor = HTMLExtractor()
    
    # 페이지 분석
    try:
        metadata = extractor.extract_metadata(html, url)
        links = extractor.extract_links(html, url)
        images = extractor.extract_images(html, url)
        structured_data = extractor.extract_structured_data(html)
        text_content = extractor.extract_text_content(html)
        html_structure = extractor.extract_html_structure(html)
        
        # 분석 결과 반환
        return {
            "metadata": metadata,
            "links": links,
            "images": images,
            "structured_data": structured_data,
            "text_content": text_content[:5000],  # 텍스트는 크기 제한
            "html_structure": html_structure
        }
    except Exception as e:
        logger.error(f"페이지 분석 실패: {str(e)}")
        return {
            "error": str(e),
            "metadata": {"url": url, "title": None, "description": None}
        }

async def fetch_and_analyze(url: str) -> Dict[str, Any]:
    """
    URL에서 페이지를 가져와 분석 (비동기 함수)
    
    Args:
        url: 분석할 URL
        
    Returns:
        Dict[str, Any]: 분석 결과
    """
    # 페이지 가져오기
    success, content = fetch_page(url)
    
    if not success:
        logger.error(f"페이지 가져오기 실패: {url} - {content}")
        return {
            "error": content,
            "metadata": {"url": url, "title": None, "description": None}
        }
    
    # 페이지 분석
    result = analyze_page(content, url)
    return result

# 추가: 간단한 인터페이스를 위한 래퍼 함수들

def extract_html_metadata(html: str, url: str) -> Dict[str, Any]:
    """
    HTML에서 메타데이터 추출하는 편의 함수
    
    Args:
        html: HTML 문자열
        url: 페이지 URL
        
    Returns:
        Dict[str, Any]: 추출된 메타데이터
    """
    try:
        extractor = HTMLExtractor()
        return extractor.extract_metadata(html, url)
    except Exception as e:
        logger.error(f"메타데이터 추출 중 오류 발생: {str(e)}")
        # 오류 시 기본 메타데이터 반환
        return {
            "url": url,
            "title": "제목 추출 실패",
            "description": "설명 추출 실패",
            "keywords": [],
            "og_image": None,
            "lang": None,
            "meta_tags": {},
            "charset": None
        } 