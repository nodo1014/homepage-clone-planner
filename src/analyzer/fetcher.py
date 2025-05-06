"""
웹사이트 콘텐츠 가져오기

이 모듈은 URL을 입력받아 웹사이트 콘텐츠를 가져오는 기능을 제공합니다.
"""
import logging
import requests
import re
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup
import httpx
import asyncio
from pathlib import Path
import os
import time

# 로깅 설정
logger = logging.getLogger(__name__)

class WebsiteFetcher:
    """웹사이트 콘텐츠 가져오기 클래스"""
    
    def __init__(self, timeout: int = 20):
        """
        웹사이트 콘텐츠 가져오기 클래스 초기화
        
        Args:
            timeout (int): 요청 타임아웃 (초)
        """
        self.timeout = timeout
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    
    def validate_url(self, url: str) -> Tuple[bool, str]:
        """
        URL 유효성 검증
        
        Args:
            url (str): 검증할 URL
            
        Returns:
            Tuple[bool, str]: (유효성 여부, 정상화된 URL 또는 오류 메시지)
        """
        # URL 입력값 정리
        url = url.strip()
        
        # URL 스키마 확인 및 추가
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            # URL 파싱
            parsed_url = urlparse(url)
            
            # 도메인 확인 - 간단한 검증만 수행
            if not parsed_url.netloc:
                return False, "유효한 도메인이 없습니다."
            
            # 기본적인 도메인 형식 검증
            # youglish.com 같은 단순 도메인도 허용하도록 조건 완화
            domain = parsed_url.netloc
            if not "." in domain:  # 최소한 하나의 점(.)은 있어야 함
                return False, "도메인 형식이 올바르지 않습니다."
            
            return True, url
        except Exception as e:
            logger.error(f"URL 유효성 검증 실패: {str(e)}")
            return False, f"URL 형식이 잘못되었습니다: {str(e)}"
    
    def fetch_content(self, url: str) -> Tuple[bool, Any]:
        """
        웹사이트 콘텐츠 가져오기
        
        Args:
            url (str): 콘텐츠를 가져올 URL
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 콘텐츠 또는 오류 메시지)
        """
        # URL 유효성 검증
        is_valid, url_or_error = self.validate_url(url)
        if not is_valid:
            return False, url_or_error
        
        # 실제 URL로 설정
        url = url_or_error
        
        try:
            # 웹사이트 콘텐츠 요청 (리다이렉션 자동 처리)
            response = requests.get(url, headers=self.headers, timeout=self.timeout, allow_redirects=True)
            
            # 응답 상태 코드 확인 (리다이렉션 후 상태 코드)
            if response.status_code != 200:
                return False, f"웹사이트에 접근할 수 없습니다. 상태 코드: {response.status_code}"
            
            # 콘텐츠 반환
            return True, response.text
        except requests.RequestException as e:
            logger.error(f"웹사이트 콘텐츠 요청 실패: {str(e)}")
            return False, f"웹사이트 콘텐츠 요청 실패: {str(e)}"
    
    async def fetch_content_async(self, url: str) -> Tuple[bool, Any]:
        """
        웹사이트 콘텐츠 비동기 가져오기
        
        Args:
            url (str): 콘텐츠를 가져올 URL
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 콘텐츠 또는 오류 메시지)
        """
        # URL 유효성 검증
        is_valid, url_or_error = self.validate_url(url)
        if not is_valid:
            return False, url_or_error
        
        # 실제 URL로 설정
        url = url_or_error
        
        try:
            # 웹사이트 콘텐츠 요청 (비동기, 리다이렉션 자동 처리)
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                
                # 응답 상태 코드 확인
                if response.status_code != 200:
                    return False, f"웹사이트에 접근할 수 없습니다. 상태 코드: {response.status_code}"
                
                # 콘텐츠 반환
                return True, response.text
        except httpx.RequestError as e:
            logger.error(f"웹사이트 콘텐츠 비동기 요청 실패: {str(e)}")
            return False, f"웹사이트 콘텐츠 요청 실패: {str(e)}"
    
    def extract_urls(self, content: str, base_url: str) -> List[str]:
        """
        웹사이트 콘텐츠에서 URL 추출
        
        Args:
            content (str): 웹사이트 콘텐츠
            base_url (str): 기본 URL
            
        Returns:
            List[str]: 추출된 URL 목록
        """
        # 결과 목록 초기화
        urls = []
        
        # BeautifulSoup 파싱
        soup = BeautifulSoup(content, 'lxml')
        
        # a 태그에서 URL 추출
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # 절대 URL로 변환
            absolute_url = urljoin(base_url, href)
            
            # 같은 도메인만 추가
            if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                urls.append(absolute_url)
        
        # 중복 제거 후 반환
        return list(set(urls))
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        웹사이트 콘텐츠에서 메타데이터 추출
        
        Args:
            content (str): 웹사이트 콘텐츠
            
        Returns:
            Dict[str, Any]: 추출된 메타데이터
        """
        metadata = {
            "title": "",
            "description": "",
            "keywords": [],
            "og_title": "",
            "og_description": "",
            "og_image": "",
            "favicon": ""
        }
        
        # BeautifulSoup 파싱
        soup = BeautifulSoup(content, 'lxml')
        
        # 제목 추출
        title_tag = soup.find('title')
        if title_tag:
            metadata["title"] = title_tag.text.strip()
        
        # 메타 태그 추출
        for meta_tag in soup.find_all('meta'):
            # 설명 추출
            if meta_tag.get('name') == 'description':
                metadata["description"] = meta_tag.get('content', '')
            
            # 키워드 추출
            elif meta_tag.get('name') == 'keywords':
                keywords = meta_tag.get('content', '')
                metadata["keywords"] = [k.strip() for k in keywords.split(',') if k.strip()]
            
            # OpenGraph 메타데이터 추출
            elif meta_tag.get('property') == 'og:title':
                metadata["og_title"] = meta_tag.get('content', '')
            elif meta_tag.get('property') == 'og:description':
                metadata["og_description"] = meta_tag.get('content', '')
            elif meta_tag.get('property') == 'og:image':
                metadata["og_image"] = meta_tag.get('content', '')
        
        # 파비콘 추출
        favicon_tag = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        if favicon_tag and favicon_tag.get('href'):
            metadata["favicon"] = favicon_tag.get('href', '')
        
        return metadata

# 편의 함수
def fetch_website_content(url: str, timeout: int = 20) -> Tuple[bool, Any]:
    """
    웹사이트 콘텐츠 가져오기 편의 함수
    
    Args:
        url (str): 콘텐츠를 가져올 URL
        timeout (int): 요청 타임아웃 (초)
        
    Returns:
        Tuple[bool, Any]: (성공 여부, 콘텐츠 또는 오류 메시지)
    """
    fetcher = WebsiteFetcher(timeout=timeout)
    return fetcher.fetch_content(url)

# 비동기 편의 함수 추가
async def fetch_website_content_async(url: str, timeout: int = 20) -> Tuple[bool, Any]:
    """
    웹사이트 콘텐츠 비동기 가져오기 편의 함수
    
    Args:
        url (str): 콘텐츠를 가져올 URL
        timeout (int): 요청 타임아웃 (초)
        
    Returns:
        Tuple[bool, Any]: (성공 여부, 콘텐츠 또는 오류 메시지)
    """
    fetcher = WebsiteFetcher(timeout=timeout)
    return await fetcher.fetch_content_async(url) 