"""
캐싱 시스템

이 모듈은 API 응답 및 웹사이트 스크래핑 결과를 캐싱하는 기능을 제공합니다.
메모리 캐시와 디스크 캐시를 모두 지원하며, TTL(Time-To-Live) 및 LRU(Least Recently Used) 알고리즘을 사용하여 캐시를 관리합니다.
"""
import os
import json
import time
import logging
import hashlib
import pickle
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from pathlib import Path
from functools import wraps
from collections import OrderedDict
import asyncio
import inspect

# 로거 설정
logger = logging.getLogger(__name__)

# 기본 캐시 유효 시간(초)
DEFAULT_TTL = 3600  # 1시간

# 기본 최대 캐시 크기
DEFAULT_MAX_SIZE = 100

# 기본 캐시 디렉토리
DEFAULT_CACHE_DIR = Path.home() / ".cloner" / "cache"


class LRUCache:
    """
    메모리 기반 LRU(Least Recently Used) 캐시 구현
    
    최대 크기에 도달하면 가장 오래된 항목을 제거합니다.
    TTL(Time-To-Live)을 사용하여 항목의 유효 기간을 관리합니다.
    """
    
    def __init__(self, max_size: int = DEFAULT_MAX_SIZE, ttl: int = DEFAULT_TTL):
        """
        LRU 캐시 초기화
        
        Args:
            max_size (int): 최대 캐시 항목 수 (기본값: 100)
            ttl (int): 캐시 항목 유효 시간(초) (기본값: 3600초)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache = OrderedDict()  # 항목 저장 (key: (value, timestamp))
        self._lock = asyncio.Lock()  # 비동기 환경에서 안전한 접근을 위한 락
    
    async def get(self, key: str) -> Tuple[bool, Any]:
        """
        캐시에서 값을 가져옵니다.
        
        Args:
            key (str): 캐시 키
            
        Returns:
            Tuple[bool, Any]: (히트 여부, 캐시된 값 또는 None)
        """
        async with self._lock:
            if key not in self._cache:
                return False, None
            
            value, timestamp = self._cache[key]
            
            # TTL 검사
            if time.time() - timestamp > self.ttl:
                # 항목이 만료됨
                del self._cache[key]
                return False, None
            
            # 캐시 히트 시 항목을 맨 뒤(가장 최근)로 이동
            self._cache.move_to_end(key)
            return True, value
    
    async def set(self, key: str, value: Any) -> None:
        """
        캐시에 값을 저장합니다.
        
        Args:
            key (str): 캐시 키
            value (Any): 저장할 값
        """
        async with self._lock:
            # 이미 존재하면 삭제하고 다시 추가 (OrderedDict 순서 유지)
            if key in self._cache:
                del self._cache[key]
            
            # 최대 크기 검사 및 관리
            if len(self._cache) >= self.max_size:
                # 가장 오래된 항목(맨 앞) 제거
                self._cache.popitem(last=False)
            
            # 새 항목 추가 (현재 타임스탬프와 함께)
            self._cache[key] = (value, time.time())
    
    async def delete(self, key: str) -> bool:
        """
        캐시에서 항목을 삭제합니다.
        
        Args:
            key (str): 삭제할 캐시 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """캐시를 완전히 비웁니다."""
        async with self._lock:
            self._cache.clear()
    
    async def get_all_keys(self) -> List[str]:
        """모든 캐시 키 목록을 반환합니다."""
        async with self._lock:
            return list(self._cache.keys())
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 통계 정보 (크기, 사용량, 만료된 항목 수 등)
        """
        async with self._lock:
            now = time.time()
            expired_count = sum(1 for _, timestamp in self._cache.values() 
                               if now - timestamp > self.ttl)
            
            return {
                "total_items": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "usage_percent": len(self._cache) / self.max_size * 100 if self.max_size > 0 else 0,
                "expired_items": expired_count
            }


class DiskCache:
    """
    디스크 기반 캐시 구현
    
    파일 시스템에 데이터를 저장하여 프로그램 재시작 후에도 캐시가 유지됩니다.
    메모리 캐시와 마찬가지로 TTL과 크기 제한을 지원합니다.
    """
    
    def __init__(
        self, 
        cache_dir: Union[str, Path] = DEFAULT_CACHE_DIR,
        max_size: int = DEFAULT_MAX_SIZE * 10,  # 디스크 캐시는 더 크게 설정
        ttl: int = DEFAULT_TTL * 24,  # 디스크 캐시는 더 오래 유지 (기본 24시간)
        extension: str = ".cache"
    ):
        """
        디스크 캐시 초기화
        
        Args:
            cache_dir (Union[str, Path]): 캐시 디렉토리 경로
            max_size (int): 최대 캐시 파일 수 (기본값: 1000)
            ttl (int): 캐시 항목 유효 시간(초) (기본값: 24시간)
            extension (str): 캐시 파일 확장자 (기본값: .cache)
        """
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.ttl = ttl
        self.extension = extension
        self._metadata_file = self.cache_dir / "metadata.json"
        self._metadata = {}  # {key: {"timestamp": timestamp, "path": file_path}}
        self._lock = asyncio.Lock()  # 비동기 환경에서 안전한 접근을 위한 락
        
        # 캐시 디렉토리 생성
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 메타데이터 로드
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """메타데이터 파일에서 캐시 정보를 로드합니다."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r') as f:
                    self._metadata = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"메타데이터 로드 실패: {str(e)}")
                self._metadata = {}
    
    def _save_metadata(self) -> None:
        """메타데이터를 파일에 저장합니다."""
        try:
            with open(self._metadata_file, 'w') as f:
                json.dump(self._metadata, f)
        except IOError as e:
            logger.error(f"메타데이터 저장 실패: {str(e)}")
    
    def _get_cache_path(self, key: str) -> Path:
        """
        캐시 키에 해당하는 파일 경로를 생성합니다.
        
        Args:
            key (str): 캐시 키
            
        Returns:
            Path: 캐시 파일 경로
        """
        # 키를 해시하여 파일 경로로 사용
        hashed_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed_key}{self.extension}"
    
    async def _cleanup_expired(self) -> None:
        """만료된 캐시 항목을 정리합니다."""
        now = time.time()
        expired_keys = []
        
        # 만료된 항목 찾기
        for key, meta in self._metadata.items():
            if now - meta["timestamp"] > self.ttl:
                expired_keys.append(key)
        
        # 만료된 항목 삭제
        for key in expired_keys:
            await self.delete(key)
    
    async def _enforce_size_limit(self) -> None:
        """캐시 크기 제한을 유지하기 위해 오래된 항목을 제거합니다."""
        # 캐시 크기가 한계를 초과하면 가장 오래된 항목부터 제거
        if len(self._metadata) > self.max_size:
            # 타임스탬프 기준으로 정렬
            sorted_keys = sorted(
                self._metadata.keys(), 
                key=lambda k: self._metadata[k]["timestamp"]
            )
            
            # 최대 크기를 유지하기 위해 오래된 항목 삭제
            items_to_remove = len(sorted_keys) - self.max_size
            for key in sorted_keys[:items_to_remove]:
                await self.delete(key)
    
    async def get(self, key: str) -> Tuple[bool, Any]:
        """
        디스크에서 캐시된 값을 가져옵니다.
        
        Args:
            key (str): 캐시 키
            
        Returns:
            Tuple[bool, Any]: (히트 여부, 캐시된 값 또는 None)
        """
        async with self._lock:
            # 메타데이터에 키가 없으면 캐시 미스
            if key not in self._metadata:
                return False, None
            
            meta = self._metadata[key]
            
            # TTL 검사
            if time.time() - meta["timestamp"] > self.ttl:
                # 만료된 항목 삭제
                await self.delete(key)
                return False, None
            
            # 캐시 파일 읽기
            try:
                cache_path = Path(meta["path"])
                if not cache_path.exists():
                    # 파일이 없으면 메타데이터에서도 제거
                    del self._metadata[key]
                    self._save_metadata()
                    return False, None
                
                with open(cache_path, 'rb') as f:
                    value = pickle.load(f)
                
                # 타임스탬프 업데이트 (LRU 동작 모방)
                meta["timestamp"] = time.time()
                self._metadata[key] = meta
                self._save_metadata()
                
                return True, value
                
            except (IOError, pickle.PickleError) as e:
                logger.error(f"캐시 읽기 실패 (키: {key}): {str(e)}")
                return False, None
    
    async def set(self, key: str, value: Any) -> None:
        """
        값을 디스크에 캐시합니다.
        
        Args:
            key (str): 캐시 키
            value (Any): 저장할 값
        """
        async with self._lock:
            # 정리 작업
            await self._cleanup_expired()
            
            # 파일 경로 생성
            cache_path = self._get_cache_path(key)
            
            try:
                # 값을 파일에 저장
                with open(cache_path, 'wb') as f:
                    pickle.dump(value, f)
                
                # 메타데이터 업데이트
                self._metadata[key] = {
                    "timestamp": time.time(),
                    "path": str(cache_path)
                }
                self._save_metadata()
                
                # 크기 제한 유지
                await self._enforce_size_limit()
                
            except (IOError, pickle.PickleError) as e:
                logger.error(f"캐시 쓰기 실패 (키: {key}): {str(e)}")
    
    async def delete(self, key: str) -> bool:
        """
        캐시에서 항목을 삭제합니다.
        
        Args:
            key (str): 삭제할 캐시 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        async with self._lock:
            if key not in self._metadata:
                return False
            
            # 파일 삭제
            try:
                cache_path = Path(self._metadata[key]["path"])
                if cache_path.exists():
                    cache_path.unlink()
            except IOError as e:
                logger.error(f"캐시 파일 삭제 실패 (키: {key}): {str(e)}")
            
            # 메타데이터에서 제거
            del self._metadata[key]
            self._save_metadata()
            
            return True
    
    async def clear(self) -> None:
        """전체 캐시를 비웁니다."""
        async with self._lock:
            # 모든 캐시 파일 삭제
            for key, meta in self._metadata.items():
                try:
                    cache_path = Path(meta["path"])
                    if cache_path.exists():
                        cache_path.unlink()
                except IOError as e:
                    logger.error(f"캐시 파일 삭제 실패 (키: {key}): {str(e)}")
            
            # 메타데이터 초기화
            self._metadata = {}
            self._save_metadata()
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        async with self._lock:
            now = time.time()
            
            # 현재 크기 계산
            current_size = len(self._metadata)
            
            # 만료된 항목 수 계산
            expired_count = sum(1 for meta in self._metadata.values() 
                               if now - meta["timestamp"] > self.ttl)
            
            # 디스크 사용량 계산
            total_size_bytes = 0
            file_count = 0
            
            for meta in self._metadata.values():
                try:
                    path = Path(meta["path"])
                    if path.exists():
                        total_size_bytes += path.stat().st_size
                        file_count += 1
                except OSError:
                    pass
            
            return {
                "total_items": current_size,
                "max_size": self.max_size,
                "ttl": self.ttl,
                "usage_percent": current_size / self.max_size * 100 if self.max_size > 0 else 0,
                "expired_items": expired_count,
                "total_size_bytes": total_size_bytes,
                "total_size_mb": total_size_bytes / 1024 / 1024,
                "file_count": file_count
            }


class CacheManager:
    """
    캐시 관리자 클래스
    
    메모리 캐시와 디스크 캐시를 통합하여 관리합니다.
    메모리 캐시에서 먼저 찾고, 없으면 디스크 캐시에서 검색합니다.
    """
    
    def __init__(
        self,
        memory_cache: Optional[LRUCache] = None,
        disk_cache: Optional[DiskCache] = None,
        use_memory_cache: bool = True,
        use_disk_cache: bool = True
    ):
        """
        캐시 관리자 초기화
        
        Args:
            memory_cache (Optional[LRUCache]): 메모리 캐시 인스턴스 (None이면 기본 설정으로 생성)
            disk_cache (Optional[DiskCache]): 디스크 캐시 인스턴스 (None이면 기본 설정으로 생성)
            use_memory_cache (bool): 메모리 캐시 사용 여부
            use_disk_cache (bool): 디스크 캐시 사용 여부
        """
        # 캐시 활성화 설정
        self.use_memory_cache = use_memory_cache
        self.use_disk_cache = use_disk_cache
        
        # 메모리 캐시 설정
        self.memory_cache = memory_cache if memory_cache is not None else LRUCache()
        
        # 디스크 캐시 설정
        self.disk_cache = disk_cache if disk_cache is not None else DiskCache()
    
    async def get(self, key: str) -> Tuple[bool, Any]:
        """
        캐시에서 값을 가져옵니다.
        메모리 캐시에서 먼저 찾고, 없으면 디스크 캐시에서 검색합니다.
        
        Args:
            key (str): 캐시 키
            
        Returns:
            Tuple[bool, Any]: (히트 여부, 캐시된 값 또는 None)
        """
        # 메모리 캐시 확인
        if self.use_memory_cache:
            hit, value = await self.memory_cache.get(key)
            if hit:
                logger.debug(f"메모리 캐시 히트: {key}")
                return True, value
        
        # 디스크 캐시 확인
        if self.use_disk_cache:
            hit, value = await self.disk_cache.get(key)
            if hit:
                logger.debug(f"디스크 캐시 히트: {key}")
                
                # 디스크에서 찾았으면 메모리에도 저장
                if self.use_memory_cache:
                    await self.memory_cache.set(key, value)
                
                return True, value
        
        logger.debug(f"캐시 미스: {key}")
        return False, None
    
    async def set(self, key: str, value: Any) -> None:
        """
        값을 캐시에 저장합니다.
        
        Args:
            key (str): 캐시 키
            value (Any): 저장할 값
        """
        # 메모리 캐시에 저장
        if self.use_memory_cache:
            await self.memory_cache.set(key, value)
        
        # 디스크 캐시에 저장
        if self.use_disk_cache:
            await self.disk_cache.set(key, value)
        
        logger.debug(f"캐시 저장: {key}")
    
    async def delete(self, key: str) -> bool:
        """
        캐시에서 항목을 삭제합니다.
        
        Args:
            key (str): 삭제할 캐시 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        memory_deleted = False
        disk_deleted = False
        
        # 메모리 캐시에서 삭제
        if self.use_memory_cache:
            memory_deleted = await self.memory_cache.delete(key)
        
        # 디스크 캐시에서 삭제
        if self.use_disk_cache:
            disk_deleted = await self.disk_cache.delete(key)
        
        return memory_deleted or disk_deleted
    
    async def clear(self) -> None:
        """
        모든 캐시를 비웁니다.
        """
        # 메모리 캐시 비우기
        if self.use_memory_cache:
            await self.memory_cache.clear()
        
        # 디스크 캐시 비우기
        if self.use_disk_cache:
            await self.disk_cache.clear()
        
        logger.debug("모든 캐시 삭제됨")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        stats = {
            "memory_cache": None,
            "disk_cache": None
        }
        
        # 메모리 캐시 통계
        if self.use_memory_cache:
            stats["memory_cache"] = await self.memory_cache.get_stats()
        
        # 디스크 캐시 통계
        if self.use_disk_cache:
            stats["disk_cache"] = await self.disk_cache.get_stats()
        
        return stats


# 함수 캐싱 데코레이터
def cached(
    ttl: int = DEFAULT_TTL, 
    key_prefix: str = "", 
    cache_manager: Optional[CacheManager] = None,
    key_builder: Optional[Callable] = None
):
    """
    함수 결과를 캐싱하는 데코레이터
    
    Args:
        ttl (int): 캐시 유효 시간(초) (기본값: 3600초)
        key_prefix (str): 캐시 키 접두사
        cache_manager (Optional[CacheManager]): 캐시 관리자 인스턴스 (None이면 생성)
        key_builder (Optional[Callable]): 캐시 키 생성 함수
        
    Returns:
        Callable: 데코레이터 함수
    """
    # 기본 CacheManager 인스턴스 생성
    if cache_manager is None:
        memory_cache = LRUCache(ttl=ttl)
        disk_cache = DiskCache(ttl=ttl)
        cache_manager = CacheManager(memory_cache=memory_cache, disk_cache=disk_cache)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_builder is not None:
                cache_key = key_builder(func, *args, **kwargs)
            else:
                # 기본 키 생성 로직 (함수 이름 + 인자 해시)
                func_name = func.__name__
                args_str = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(args_str.encode()).hexdigest()
                cache_key = f"{key_prefix}{func_name}_{args_hash}"
            
            # 캐시에서 조회
            hit, cached_result = await cache_manager.get(cache_key)
            if hit:
                return cached_result
            
            # 캐시 미스: 함수 실행
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 결과 캐싱
            await cache_manager.set(cache_key, result)
            
            return result
        
        return wrapper
    
    return decorator


# API 응답 캐싱 데코레이터
def cached_api_response(
    ttl: int = DEFAULT_TTL,
    cache_error_responses: bool = False,
    key_prefix: str = "api_",
    cache_manager: Optional[CacheManager] = None
):
    """
    API 응답을 캐싱하는 데코레이터
    
    API 클라이언트 메소드에 적용하기 위한 특수 데코레이터입니다.
    (success, data) 형식의 반환값을 처리합니다.
    
    Args:
        ttl (int): 캐시 유효 시간(초) (기본값: 3600초)
        cache_error_responses (bool): 오류 응답도 캐싱할지 여부 (기본값: False)
        key_prefix (str): 캐시 키 접두사
        cache_manager (Optional[CacheManager]): 캐시 관리자 인스턴스
        
    Returns:
        Callable: 데코레이터 함수
    """
    # 기본 CacheManager 인스턴스 생성
    if cache_manager is None:
        memory_cache = LRUCache(ttl=ttl)
        disk_cache = DiskCache(ttl=ttl)
        cache_manager = CacheManager(memory_cache=memory_cache, disk_cache=disk_cache)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성 (API 메소드 이름 + 인자 해시)
            func_name = func.__name__
            # 첫 번째 인자(self)는 제외
            key_args = args[1:] if len(args) > 0 else args
            
            # 인자를 문자열로 변환
            args_str = str(key_args) + str(sorted(kwargs.items()))
            args_hash = hashlib.md5(args_str.encode()).hexdigest()
            cache_key = f"{key_prefix}{func_name}_{args_hash}"
            
            # 캐시에서 조회
            hit, cached_result = await cache_manager.get(cache_key)
            if hit:
                return cached_result
            
            # 캐시 미스: API 호출 실행
            result = await func(*args, **kwargs)
            
            # API 성공 응답 또는 캐시 오류 설정을 확인
            success, data = result
            if success or cache_error_responses:
                # 결과 캐싱
                await cache_manager.set(cache_key, result)
            
            return result
        
        return wrapper
    
    return decorator 