"""
WebsiteFetcher 테스트

이 모듈은 src/analyzer/fetcher.py의 기능을 테스트합니다.
"""
import os
import sys
import pytest

# 프로젝트 루트 경로를 시스템 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.analyzer.fetcher import WebsiteFetcher, fetch_website_content

# 테스트 URL
TEST_URL = "https://example.com"
INVALID_URL = "invalid-url"
NONEXISTENT_URL = "https://nonexistent-domain-123456789.com"

class TestWebsiteFetcher:
    """WebsiteFetcher 클래스 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.fetcher = WebsiteFetcher(timeout=10)
    
    def test_validate_url_valid(self):
        """유효한 URL 검증 테스트"""
        is_valid, url = self.fetcher.validate_url(TEST_URL)
        assert is_valid == True
        assert url == TEST_URL
    
    def test_validate_url_no_scheme(self):
        """스키마가 없는 URL 검증 테스트"""
        is_valid, url = self.fetcher.validate_url("example.com")
        assert is_valid == True
        assert url == "https://example.com"
    
    def test_validate_url_invalid(self):
        """잘못된 URL 검증 테스트"""
        is_valid, url = self.fetcher.validate_url(INVALID_URL)
        assert is_valid == False
    
    def test_fetch_content_valid(self):
        """유효한 URL에서 콘텐츠 가져오기 테스트"""
        success, content = self.fetcher.fetch_content(TEST_URL)
        assert success == True
        assert isinstance(content, str)
        assert len(content) > 0
    
    def test_fetch_content_nonexistent(self):
        """존재하지 않는 URL에서 콘텐츠 가져오기 테스트"""
        success, content = self.fetcher.fetch_content(NONEXISTENT_URL)
        assert success == False
    
    def test_extract_metadata(self):
        """메타데이터 추출 테스트"""
        success, content = self.fetcher.fetch_content(TEST_URL)
        assert success == True
        
        metadata = self.fetcher.extract_metadata(content)
        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert len(metadata["title"]) > 0
    
    def test_extract_urls(self):
        """URL 추출 테스트"""
        success, content = self.fetcher.fetch_content(TEST_URL)
        assert success == True
        
        urls = self.fetcher.extract_urls(content, TEST_URL)
        assert isinstance(urls, list)

def test_fetch_website_content():
    """fetch_website_content 편의 함수 테스트"""
    success, content = fetch_website_content(TEST_URL)
    assert success == True
    assert isinstance(content, str)
    assert len(content) > 0 