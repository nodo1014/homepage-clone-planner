"""
URL 유효성 검사 모듈

이 모듈은 URL의 유효성을 검사하고 정규화하는 기능을 제공합니다.
"""
import re
import logging
import urllib.parse
from typing import Tuple, Optional

# 로거 설정
logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    """
    URL 정규화 함수
    
    Args:
        url: 정규화할 URL 문자열
        
    Returns:
        str: 정규화된 URL
    """
    url = url.strip()
    
    # URL이 스킴(http://, https://)으로 시작하지 않으면 http:// 추가
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
        logger.debug(f"스킴이 없는 URL에 'http://' 추가: {url}")
    
    # 후행 슬래시 정규화
    parsed = urllib.parse.urlparse(url)
    if parsed.path == '':
        # 경로가 없으면 / 추가
        url = url + '/'
        logger.debug(f"경로가 없는 URL에 '/' 추가: {url}")
    
    return url

def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    URL 유효성 검사 함수
    
    Args:
        url: 검사할 URL 문자열
        
    Returns:
        Tuple[bool, Optional[str]]: (유효성 여부, 오류 메시지)
    """
    if not url or not isinstance(url, str):
        return False, "URL이 비어 있거나 문자열이 아닙니다."
    
    url = url.strip()
    
    # 기본적인 URL 형식 검사
    url_pattern = re.compile(
        r'^(https?://)?' # http:// 또는 https:// (선택 사항)
        r'([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+' # 도메인 이름
        r'[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?' # 서브 도메인
        r'(\.[a-zA-Z]{2,})' # 최상위 도메인
        r'(/[a-zA-Z0-9._~:/?#[\]@!$&\'()*+,;=]*)?' # 경로 (선택 사항)
        r'$'
    )
    
    if not url_pattern.match(url):
        logger.warning(f"유효하지 않은 URL 형식: {url}")
        return False, "유효하지 않은 URL 형식입니다."
    
    # URL 정규화
    normalized_url = normalize_url(url)
    
    logger.debug(f"URL 유효성 검사 통과: {normalized_url}")
    return True, normalized_url

def is_same_domain(url1: str, url2: str) -> bool:
    """
    두 URL이 같은 도메인인지 확인
    
    Args:
        url1: 첫 번째 URL
        url2: 두 번째 URL
        
    Returns:
        bool: 같은 도메인 여부
    """
    # URL 정규화
    url1 = normalize_url(url1)
    url2 = normalize_url(url2)
    
    # 도메인 추출
    domain1 = urllib.parse.urlparse(url1).netloc
    domain2 = urllib.parse.urlparse(url2).netloc
    
    # www. 접두사 제거
    domain1 = domain1.replace('www.', '')
    domain2 = domain2.replace('www.', '')
    
    return domain1 == domain2

def get_base_url(url: str) -> str:
    """
    기본 URL 추출 (스킴 + 도메인)
    
    Args:
        url: URL 문자열
        
    Returns:
        str: 기본 URL (스킴 + 도메인)
    """
    # URL 정규화
    url = normalize_url(url)
    
    # 파싱
    parsed = urllib.parse.urlparse(url)
    
    # 기본 URL 생성 (스킴 + 도메인)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    return base_url

def join_url(base_url: str, path: str) -> str:
    """
    기본 URL과 경로 결합
    
    Args:
        base_url: 기본 URL
        path: 결합할 경로
        
    Returns:
        str: 결합된 URL
    """
    # URL 정규화
    base_url = normalize_url(base_url)
    
    # 경로에서 선행 슬래시 제거
    if path.startswith('/'):
        path = path[1:]
    
    # 기본 URL에서 후행 슬래시 확인
    if not base_url.endswith('/'):
        base_url = base_url + '/'
    
    # URL 결합
    joined_url = base_url + path
    
    return joined_url 