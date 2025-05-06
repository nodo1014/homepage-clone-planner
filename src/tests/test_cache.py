"""
캐싱 시스템 테스트

이 모듈은 API 응답 및 웹사이트 스크래핑 결과 캐싱 기능을 테스트합니다.
"""
import pytest
import asyncio
import time
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from src.utils.cache import (
    LRUCache, 
    DiskCache, 
    CacheManager, 
    cached, 
    cached_api_response,
    DEFAULT_TTL,
    DEFAULT_MAX_SIZE
)


# 테스트에 사용할 임시 캐시 디렉토리
@pytest.fixture
def temp_cache_dir():
    """테스트용 임시 캐시 디렉토리를 생성합니다."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # 테스트 후 정리
    shutil.rmtree(temp_dir, ignore_errors=True)


# LRUCache 테스트용 fixture
@pytest.fixture
def lru_cache():
    """LRUCache 인스턴스를 생성합니다."""
    return LRUCache(max_size=5, ttl=10)


# DiskCache 테스트용 fixture
@pytest.fixture
def disk_cache(temp_cache_dir):
    """DiskCache 인스턴스를 생성합니다."""
    return DiskCache(cache_dir=temp_cache_dir, max_size=5, ttl=10)


# CacheManager 테스트용 fixture
@pytest.fixture
def cache_manager(lru_cache, disk_cache):
    """CacheManager 인스턴스를 생성합니다."""
    return CacheManager(memory_cache=lru_cache, disk_cache=disk_cache)


# =========== LRUCache 테스트 ===========
@pytest.mark.asyncio
async def test_lru_cache_set_get(lru_cache):
    """LRUCache의 set/get 기능 테스트"""
    # 캐시 항목 저장
    await lru_cache.set("key1", "value1")
    
    # 캐시 항목 조회
    hit, value = await lru_cache.get("key1")
    
    # 검증
    assert hit is True
    assert value == "value1"
    
    # 없는 키 조회
    hit, value = await lru_cache.get("non_existent_key")
    assert hit is False
    assert value is None


@pytest.mark.asyncio
async def test_lru_cache_delete(lru_cache):
    """LRUCache의 delete 기능 테스트"""
    # 캐시 항목 저장
    await lru_cache.set("key1", "value1")
    
    # 캐시 항목 삭제
    deleted = await lru_cache.delete("key1")
    
    # 검증
    assert deleted is True
    
    # 삭제 후 조회
    hit, value = await lru_cache.get("key1")
    assert hit is False
    assert value is None
    
    # 없는 키 삭제
    deleted = await lru_cache.delete("non_existent_key")
    assert deleted is False


@pytest.mark.asyncio
async def test_lru_cache_clear(lru_cache):
    """LRUCache의 clear 기능 테스트"""
    # 여러 캐시 항목 저장
    await lru_cache.set("key1", "value1")
    await lru_cache.set("key2", "value2")
    
    # 캐시 비우기
    await lru_cache.clear()
    
    # 검증
    hit1, _ = await lru_cache.get("key1")
    hit2, _ = await lru_cache.get("key2")
    assert hit1 is False
    assert hit2 is False


@pytest.mark.asyncio
async def test_lru_cache_max_size(lru_cache):
    """LRUCache의 최대 크기 제한 기능 테스트"""
    # 최대 크기(5) + 1개의 항목 저장
    for i in range(6):
        await lru_cache.set(f"key{i}", f"value{i}")
    
    # 가장 오래된 항목(key0)은 제거되어야 함
    hit, value = await lru_cache.get("key0")
    assert hit is False
    
    # 나머지 항목은 남아있어야 함
    for i in range(1, 6):
        hit, value = await lru_cache.get(f"key{i}")
        assert hit is True
        assert value == f"value{i}"


@pytest.mark.asyncio
async def test_lru_cache_lru_behavior(lru_cache):
    """LRUCache의 LRU(Least Recently Used) 동작 테스트"""
    # 최대 크기만큼 항목 저장
    for i in range(5):
        await lru_cache.set(f"key{i}", f"value{i}")
    
    # key0을 접근하여 최근 사용 항목으로 만듦
    await lru_cache.get("key0")
    
    # 새 항목 추가 (key1이 제거되어야 함)
    await lru_cache.set("key5", "value5")
    
    # key0은 최근에 사용되었으므로 남아있어야 함
    hit, value = await lru_cache.get("key0")
    assert hit is True
    
    # key1은 가장 오래된 항목이므로 제거되어야 함
    hit, value = await lru_cache.get("key1")
    assert hit is False


@pytest.mark.asyncio
async def test_lru_cache_ttl(lru_cache):
    """LRUCache의 TTL(Time-To-Live) 기능 테스트"""
    # 캐시 항목 저장
    await lru_cache.set("key1", "value1")
    
    # TTL 이전에는 사용 가능
    hit, value = await lru_cache.get("key1")
    assert hit is True
    
    # TTL 만료 시뮬레이션
    with patch.object(time, 'time', return_value=time.time() + 11):  # TTL + 1초 후
        # TTL 이후에는 만료됨
        hit, value = await lru_cache.get("key1")
        assert hit is False


@pytest.mark.asyncio
async def test_lru_cache_stats(lru_cache):
    """LRUCache의 통계 기능 테스트"""
    # 몇 개의 항목 저장
    await lru_cache.set("key1", "value1")
    await lru_cache.set("key2", "value2")
    
    # 통계 정보 가져오기
    stats = await lru_cache.get_stats()
    
    # 검증
    assert stats["total_items"] == 2
    assert stats["max_size"] == 5
    assert stats["ttl"] == 10
    assert stats["usage_percent"] == 40.0  # 2/5 * 100


# =========== DiskCache 테스트 ===========
@pytest.mark.asyncio
async def test_disk_cache_set_get(disk_cache):
    """DiskCache의 set/get 기능 테스트"""
    # 캐시 항목 저장
    await disk_cache.set("key1", "value1")
    
    # 캐시 항목 조회
    hit, value = await disk_cache.get("key1")
    
    # 검증
    assert hit is True
    assert value == "value1"
    
    # 없는 키 조회
    hit, value = await disk_cache.get("non_existent_key")
    assert hit is False
    assert value is None


@pytest.mark.asyncio
async def test_disk_cache_delete(disk_cache):
    """DiskCache의 delete 기능 테스트"""
    # 캐시 항목 저장
    await disk_cache.set("key1", "value1")
    
    # 캐시 항목 삭제
    deleted = await disk_cache.delete("key1")
    
    # 검증
    assert deleted is True
    
    # 삭제 후 조회
    hit, value = await disk_cache.get("key1")
    assert hit is False
    assert value is None


@pytest.mark.asyncio
async def test_disk_cache_clear(disk_cache):
    """DiskCache의 clear 기능 테스트"""
    # 여러 캐시 항목 저장
    await disk_cache.set("key1", "value1")
    await disk_cache.set("key2", "value2")
    
    # 캐시 비우기
    await disk_cache.clear()
    
    # 검증
    hit1, _ = await disk_cache.get("key1")
    hit2, _ = await disk_cache.get("key2")
    assert hit1 is False
    assert hit2 is False


@pytest.mark.asyncio
async def test_disk_cache_max_size(disk_cache):
    """DiskCache의 최대 크기 제한 기능 테스트"""
    # 최대 크기(5) + 1개의 항목 저장
    for i in range(6):
        await disk_cache.set(f"key{i}", f"value{i}")
    
    # 캐시 크기 확인 (1개는 제거되어야 함)
    stats = await disk_cache.get_stats()
    assert stats["total_items"] <= 5


@pytest.mark.asyncio
async def test_disk_cache_ttl(disk_cache):
    """DiskCache의 TTL(Time-To-Live) 기능 테스트"""
    # 캐시 항목 저장
    await disk_cache.set("key1", "value1")
    
    # TTL 이전에는 사용 가능
    hit, value = await disk_cache.get("key1")
    assert hit is True
    
    # TTL 만료 시뮬레이션
    with patch.object(time, 'time', return_value=time.time() + 11):  # TTL + 1초 후
        # TTL 이후에는 만료됨
        hit, value = await disk_cache.get("key1")
        assert hit is False


@pytest.mark.asyncio
async def test_disk_cache_persistence(temp_cache_dir):
    """DiskCache의 영속성 테스트 (프로그램 재시작 시뮬레이션)"""
    # 첫 번째 캐시 인스턴스로 데이터 저장
    cache1 = DiskCache(cache_dir=temp_cache_dir, max_size=5, ttl=10)
    await cache1.set("key1", "value1")
    
    # 두 번째 캐시 인스턴스 (같은 디렉토리 사용)
    cache2 = DiskCache(cache_dir=temp_cache_dir, max_size=5, ttl=10)
    
    # 두 번째 인스턴스에서 데이터 조회
    hit, value = await cache2.get("key1")
    
    # 검증
    assert hit is True
    assert value == "value1"


@pytest.mark.asyncio
async def test_disk_cache_complex_data(disk_cache):
    """DiskCache의 복잡한 자료구조 저장 테스트"""
    # 복잡한 데이터 구조
    complex_data = {
        "list": [1, 2, 3, 4],
        "dict": {"a": 1, "b": 2},
        "set": set([1, 2, 3]),
        "tuple": (1, "string", 3.14),
        "none": None,
        "nested": {"inner": [{"deep": "value"}]}
    }
    
    # 저장
    await disk_cache.set("complex", complex_data)
    
    # 조회
    hit, value = await disk_cache.get("complex")
    
    # 검증
    assert hit is True
    assert value == complex_data


# =========== CacheManager 테스트 ===========
@pytest.mark.asyncio
async def test_cache_manager_memory_first(cache_manager):
    """CacheManager의 메모리 우선 조회 테스트"""
    # 메모리에만 저장
    await cache_manager.memory_cache.set("key1", "memory_value")
    
    # CacheManager로 조회
    hit, value = await cache_manager.get("key1")
    
    # 검증
    assert hit is True
    assert value == "memory_value"


@pytest.mark.asyncio
async def test_cache_manager_disk_fallback(cache_manager):
    """CacheManager의 디스크 폴백 테스트"""
    # 디스크에만 저장
    await cache_manager.disk_cache.set("key1", "disk_value")
    
    # CacheManager로 조회
    hit, value = await cache_manager.get("key1")
    
    # 검증
    assert hit is True
    assert value == "disk_value"
    
    # 메모리에도 복사되었는지 확인
    memory_hit, memory_value = await cache_manager.memory_cache.get("key1")
    assert memory_hit is True
    assert memory_value == "disk_value"


@pytest.mark.asyncio
async def test_cache_manager_set(cache_manager):
    """CacheManager의 set 기능 테스트"""
    # CacheManager로 저장
    await cache_manager.set("key1", "value1")
    
    # 메모리와 디스크 모두에 저장되었는지 확인
    memory_hit, memory_value = await cache_manager.memory_cache.get("key1")
    disk_hit, disk_value = await cache_manager.disk_cache.get("key1")
    
    assert memory_hit is True
    assert memory_value == "value1"
    assert disk_hit is True
    assert disk_value == "value1"


@pytest.mark.asyncio
async def test_cache_manager_delete(cache_manager):
    """CacheManager의 delete 기능 테스트"""
    # 데이터 저장
    await cache_manager.set("key1", "value1")
    
    # 삭제
    deleted = await cache_manager.delete("key1")
    
    # 검증
    assert deleted is True
    
    # 메모리와 디스크 모두에서 삭제되었는지 확인
    memory_hit, _ = await cache_manager.memory_cache.get("key1")
    disk_hit, _ = await cache_manager.disk_cache.get("key1")
    
    assert memory_hit is False
    assert disk_hit is False


@pytest.mark.asyncio
async def test_cache_manager_clear(cache_manager):
    """CacheManager의 clear 기능 테스트"""
    # 데이터 저장
    await cache_manager.set("key1", "value1")
    await cache_manager.set("key2", "value2")
    
    # 캐시 비우기
    await cache_manager.clear()
    
    # 검증
    memory_stats = await cache_manager.memory_cache.get_stats()
    disk_stats = await cache_manager.disk_cache.get_stats()
    
    assert memory_stats["total_items"] == 0
    assert disk_stats["total_items"] == 0


@pytest.mark.asyncio
async def test_cache_manager_disabled_caches(temp_cache_dir):
    """CacheManager의 캐시 비활성화 기능 테스트"""
    memory_cache = LRUCache(max_size=5, ttl=10)
    disk_cache = DiskCache(cache_dir=temp_cache_dir, max_size=5, ttl=10)
    
    # 디스크 캐시 비활성화
    manager = CacheManager(
        memory_cache=memory_cache,
        disk_cache=disk_cache,
        use_memory_cache=True,
        use_disk_cache=False
    )
    
    # 저장
    await manager.set("key1", "value1")
    
    # 메모리에만 저장되고 디스크에는 저장되지 않아야 함
    memory_hit, _ = await memory_cache.get("key1")
    disk_hit, _ = await disk_cache.get("key1")
    
    assert memory_hit is True
    assert disk_hit is False


# =========== 데코레이터 테스트 ===========
@pytest.mark.asyncio
async def test_cached_decorator():
    """cached 데코레이터 테스트"""
    # 임시 캐시 파일을 위한 디렉토리
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 캐싱할 함수 (첫 호출 시 1초 지연)
        call_count = 0
        
        @cached(ttl=10, key_prefix="test_")
        async def expensive_function(arg1, arg2=None):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # 작업 시뮬레이션
            return f"Result: {arg1}, {arg2}"
        
        # 첫 번째 호출 (캐시 미스)
        start_time = time.time()
        result1 = await expensive_function("value1", arg2="value2")
        first_call_time = time.time() - start_time
        
        # 두 번째 호출 (캐시 히트)
        start_time = time.time()
        result2 = await expensive_function("value1", arg2="value2")
        second_call_time = time.time() - start_time
        
        # 다른 인자로 호출 (캐시 미스)
        result3 = await expensive_function("value3", arg2="value4")
        
        # 검증
        assert result1 == result2 == "Result: value1, value2"
        assert result3 == "Result: value3, value4"
        assert call_count == 2  # 캐시 히트로 인해 실제 함수는 2번만 호출됨
        assert second_call_time < first_call_time  # 캐시 히트는 더 빨라야 함
        
    finally:
        # 임시 디렉토리 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cached_api_response_decorator():
    """cached_api_response 데코레이터 테스트"""
    # API 응답을 반환하는 모의 API 클라이언트 메소드
    call_count = 0
    
    class MockApiClient:
        @cached_api_response(ttl=10)
        async def api_method(self, param1, param2=None):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # API 호출 시뮬레이션
            return True, {"result": f"data_{param1}_{param2}"}
        
        @cached_api_response(ttl=10, cache_error_responses=True)
        async def api_method_with_error(self, param):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return False, {"error": "API error"}
    
    client = MockApiClient()
    
    # 성공 응답 테스트
    # 첫 번째 호출 (캐시 미스)
    success1, data1 = await client.api_method("a", "b")
    
    # 두 번째 호출 (캐시 히트)
    success2, data2 = await client.api_method("a", "b")
    
    # 다른 인자로 호출 (캐시 미스)
    success3, data3 = await client.api_method("c", "d")
    
    # 검증
    assert success1 is True and success2 is True
    assert data1 == data2
    assert data1 == {"result": "data_a_b"}
    assert data3 == {"result": "data_c_d"}
    assert call_count == 2  # 캐시 히트로 인해 실제 API는 2번만 호출됨
    
    # 오류 응답 캐싱 테스트
    # 첫 번째 호출
    call_count = 0
    success4, error1 = await client.api_method_with_error("error")
    
    # 두 번째 호출 (캐시 히트)
    success5, error2 = await client.api_method_with_error("error")
    
    # 검증
    assert success4 is False and success5 is False
    assert error1 == error2
    assert error1 == {"error": "API error"}
    assert call_count == 1  # 오류 응답도 캐싱되므로 1번만 호출 