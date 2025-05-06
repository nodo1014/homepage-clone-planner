"""
API 모니터링 테스트

이 모듈은 API 호출 모니터링 및 사용량 제한 기능을 테스트합니다.
"""
import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import shutil
from pathlib import Path

from src.api.api_monitor import (
    ApiMonitor, 
    ApiUsageData, 
    ApiMonitorDecorator, 
    get_api_monitor,
    monitor_api_call
)


# 테스트용 임시 디렉토리
@pytest.fixture
def temp_monitor_dir():
    """테스트용 임시 모니터링 데이터 디렉토리"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # 테스트 후 정리
    shutil.rmtree(temp_dir, ignore_errors=True)


# ApiMonitor 테스트용 fixture
@pytest.fixture
def api_monitor(temp_monitor_dir):
    """테스트용 ApiMonitor 인스턴스"""
    monitor = ApiMonitor(data_dir=temp_monitor_dir, auto_save=False)
    return monitor


# ========== ApiMonitor 기본 기능 테스트 ==========
@pytest.mark.asyncio
async def test_record_api_call(api_monitor):
    """API 호출 기록 기능 테스트"""
    # API 호출 기록
    await api_monitor.record_api_call(
        api_name="openai",
        endpoint="/v1/chat/completions",
        success=True,
        tokens={"prompt": 10, "completion": 20, "total": 30},
        cost=0.01,
        duration=0.5
    )
    
    # 기록된 데이터 확인
    stats = await api_monitor.get_usage_stats("openai")
    
    # 검증
    assert stats["total_calls"] == 1
    assert stats["success_count"] == 1
    assert stats["error_count"] == 0
    assert stats["success_rate"] == 100.0
    assert stats["total_cost"] == 0.01
    assert stats["tokens"]["prompt"] == 10
    assert stats["tokens"]["completion"] == 20
    assert stats["tokens"]["total"] == 30


@pytest.mark.asyncio
async def test_record_multiple_api_calls(api_monitor):
    """여러 API 호출 기록 테스트"""
    # 여러 API 호출 기록
    for i in range(3):
        await api_monitor.record_api_call(
            api_name="openai",
            endpoint="/v1/chat/completions",
            success=True,
            cost=0.01,
        )
    
    # 실패 케이스도 기록
    await api_monitor.record_api_call(
        api_name="openai",
        endpoint="/v1/chat/completions",
        success=False,
    )
    
    # 다른 API 호출 기록
    await api_monitor.record_api_call(
        api_name="claude",
        endpoint="/v1/messages",
        success=True,
        cost=0.02,
    )
    
    # 전체 통계 확인
    stats = await api_monitor.get_usage_stats()
    
    # 검증: 전체 요약
    assert "_summary" in stats
    assert stats["_summary"]["total_calls"] == 5
    assert stats["_summary"]["success_count"] == 4
    assert stats["_summary"]["error_count"] == 1
    assert stats["_summary"]["success_rate"] == 80.0
    assert stats["_summary"]["total_cost"] == 0.05
    
    # 검증: OpenAI 통계
    assert "openai" in stats
    assert stats["openai"]["total_calls"] == 4
    assert stats["openai"]["success_count"] == 3
    assert stats["openai"]["error_count"] == 1
    assert stats["openai"]["success_rate"] == 75.0
    assert stats["openai"]["total_cost"] == 0.03
    
    # 검증: Claude 통계
    assert "claude" in stats
    assert stats["claude"]["total_calls"] == 1
    assert stats["claude"]["success_count"] == 1
    assert stats["claude"]["error_count"] == 0
    assert stats["claude"]["success_rate"] == 100.0
    assert stats["claude"]["total_cost"] == 0.02


@pytest.mark.asyncio
async def test_set_and_check_limits(api_monitor):
    """API 사용량 제한 설정 및 확인 테스트"""
    # 제한 설정
    await api_monitor.set_limit("openai", "hourly", 5)
    await api_monitor.set_limit("openai", "daily", 10)
    
    # 제한 이내의 호출 기록
    for i in range(4):
        await api_monitor.record_api_call(
            api_name="openai",
            endpoint="/v1/chat/completions",
            success=True
        )
    
    # 제한 확인 (아직 초과 안 함)
    exceeded, limit_type = await api_monitor.check_limits("openai")
    assert not exceeded
    assert limit_type is None
    
    # 시간당 제한 초과
    await api_monitor.record_api_call(
        api_name="openai",
        endpoint="/v1/chat/completions",
        success=True
    )
    
    # 제한 확인 (이제 초과함)
    exceeded, limit_type = await api_monitor.check_limits("openai")
    assert exceeded
    assert limit_type == "hourly"
    
    # 다른 API 제한 설정 및 확인
    await api_monitor.set_limit("claude", "daily", 3)
    
    for i in range(2):
        await api_monitor.record_api_call(
            api_name="claude",
            endpoint="/v1/messages",
            success=True
        )
    
    # 아직 제한에 도달하지 않음
    exceeded, limit_type = await api_monitor.check_limits("claude")
    assert not exceeded
    
    # 제한 초과
    await api_monitor.record_api_call(
        api_name="claude",
        endpoint="/v1/messages",
        success=True
    )
    
    exceeded, limit_type = await api_monitor.check_limits("claude")
    assert exceeded
    assert limit_type == "daily"


@pytest.mark.asyncio
async def test_set_cost_info(api_monitor):
    """비용 정보 설정 테스트"""
    # 비용 정보 설정
    await api_monitor.set_cost_info(
        api_name="openai",
        cost_per_call=0.02,
        monthly_budget=10.0
    )
    
    # API 사용 기록
    await api_monitor.record_api_call(
        api_name="openai",
        endpoint="/v1/chat/completions",
        success=True,
        cost=0.02
    )
    
    # 통계 확인
    stats = await api_monitor.get_usage_stats("openai")
    
    # 검증
    assert stats["total_cost"] == 0.02
    assert stats["this_month"]["budget"] == 10.0
    assert stats["this_month"]["budget_used_percent"] == 0.2  # 0.02 / 10.0 * 100
    
    # 월별 예산 제한 설정 및 확인
    # 예산의 절반 사용
    for i in range(249):  # 이미 0.02 소비, 추가로 4.98 소비하면 총 5.0
        await api_monitor.record_api_call(
            api_name="openai",
            endpoint="/v1/chat/completions",
            success=True,
            cost=0.02
        )
    
    # 제한 확인 (예산의 50%는 아직 초과하지 않음)
    exceeded, limit_type = await api_monitor.check_limits("openai")
    assert not exceeded
    
    # 예산 모두 사용
    for i in range(250):  # 추가로 5.0 소비하면 총 10.0
        await api_monitor.record_api_call(
            api_name="openai",
            endpoint="/v1/chat/completions",
            success=True,
            cost=0.02
        )
    
    # 제한 확인 (이제 예산 초과)
    exceeded, limit_type = await api_monitor.check_limits("openai")
    assert exceeded
    assert limit_type == "budget"


@pytest.mark.asyncio
async def test_clear_usage_data(api_monitor):
    """사용량 데이터 초기화 테스트"""
    # API 사용 기록
    await api_monitor.record_api_call(
        api_name="openai",
        endpoint="/v1/chat/completions",
        success=True
    )
    
    await api_monitor.record_api_call(
        api_name="claude",
        endpoint="/v1/messages",
        success=True
    )
    
    # 제한 설정
    await api_monitor.set_limit("openai", "hourly", 10)
    await api_monitor.set_limit("claude", "daily", 20)
    
    # 특정 API 데이터만 초기화
    await api_monitor.clear_usage_data("openai")
    
    # 확인
    openai_stats = await api_monitor.get_usage_stats("openai")
    claude_stats = await api_monitor.get_usage_stats("claude")
    
    # OpenAI 데이터는 초기화되었지만 제한은 유지
    assert openai_stats["total_calls"] == 0
    assert openai_stats["limits"]["hourly"] == 10
    
    # Claude 데이터는 그대로
    assert claude_stats["total_calls"] == 1
    assert claude_stats["limits"]["daily"] == 20
    
    # 전체 데이터 초기화
    await api_monitor.clear_usage_data()
    
    # 확인
    openai_stats = await api_monitor.get_usage_stats("openai")
    claude_stats = await api_monitor.get_usage_stats("claude")
    
    # 모든 데이터 초기화되었지만 제한은 유지
    assert openai_stats["total_calls"] == 0
    assert openai_stats["limits"]["hourly"] == 10
    assert claude_stats["total_calls"] == 0
    assert claude_stats["limits"]["daily"] == 20


@pytest.mark.asyncio
async def test_save_and_load_data(temp_monitor_dir):
    """데이터 저장 및 로드 테스트"""
    # 첫 번째 모니터 인스턴스 생성 및 데이터 기록
    monitor1 = ApiMonitor(data_dir=temp_monitor_dir, auto_save=False)
    
    await monitor1.record_api_call(
        api_name="openai",
        endpoint="/v1/chat/completions",
        success=True,
        tokens={"prompt": 10, "completion": 20, "total": 30},
        cost=0.01
    )
    
    await monitor1.set_limit("openai", "hourly", 100)
    await monitor1.set_cost_info("openai", cost_per_call=0.02, monthly_budget=50.0)
    
    # 데이터 저장
    await monitor1.save_data()
    
    # 두 번째 모니터 인스턴스 생성 (데이터 로드)
    monitor2 = ApiMonitor(data_dir=temp_monitor_dir, auto_save=False)
    
    # 데이터가 제대로 로드되었는지 확인
    stats = await monitor2.get_usage_stats("openai")
    
    # 검증
    assert stats["total_calls"] == 1
    assert stats["total_cost"] == 0.01
    assert stats["tokens"]["total"] == 30
    assert stats["limits"]["hourly"] == 100
    assert stats["this_month"]["budget"] == 50.0


# ========== ApiMonitorDecorator 테스트 ==========
@pytest.mark.asyncio
async def test_api_monitor_decorator(api_monitor):
    """API 모니터링 데코레이터 테스트"""
    # 모의 API 클라이언트 메소드
    async def mock_api_method(endpoint, success=True, tokens=None):
        if not success:
            return False, {"error": "API error"}
        
        result = {"result": "success"}
        if tokens:
            result["usage"] = {
                "prompt_tokens": tokens["prompt"],
                "completion_tokens": tokens["completion"],
                "total_tokens": tokens["prompt"] + tokens["completion"]
            }
        
        return True, result
    
    # 데코레이터 적용
    decorator = ApiMonitorDecorator(
        api_monitor=api_monitor,
        api_name="test_api",
        check_limits=True
    )
    
    decorated_method = decorator(mock_api_method)
    
    # 제한 설정
    await api_monitor.set_limit("test_api", "hourly", 3)
    
    # 성공 케이스 호출
    success, data = await decorated_method(
        endpoint="/test",
        tokens={"prompt": 10, "completion": 20}
    )
    
    # 결과 검증
    assert success is True
    assert data["result"] == "success"
    
    # 실패 케이스 호출
    success, data = await decorated_method(
        endpoint="/test",
        success=False
    )
    
    # 결과 검증
    assert success is False
    assert data["error"] == "API error"
    
    # 세 번째 호출 (제한에 도달)
    await decorated_method(endpoint="/test")
    
    # 네 번째 호출 (제한 초과)
    success, data = await decorated_method(endpoint="/test")
    
    # 제한 초과로 인한 오류 응답 확인
    assert success is False
    assert "API 사용량 제한 초과" in data["error"]
    assert "hourly" in data["details"]
    
    # API 사용량 통계 확인
    stats = await api_monitor.get_usage_stats("test_api")
    
    # 검증: 3번의 성공적인 API 호출만 기록되어야 함 (4번째는 제한 초과로 호출되지 않음)
    assert stats["total_calls"] == 3
    assert stats["success_count"] == 2
    assert stats["error_count"] == 1


# ========== 글로벌 API 모니터 테스트 ==========
@pytest.mark.asyncio
async def test_global_api_monitor():
    """글로벌 API 모니터 인스턴스 테스트"""
    # 전역 모니터 인스턴스 가져오기
    monitor = get_api_monitor()
    
    # 기본 인스턴스 확인
    assert monitor is not None
    assert isinstance(monitor, ApiMonitor)
    
    # 두 번째 호출 시 동일한 인스턴스 반환 확인
    monitor2 = get_api_monitor()
    assert monitor is monitor2
    
    # 간편 모니터링 함수 테스트
    with patch('src.api.api_monitor.get_api_monitor') as mock_get_monitor:
        mock_monitor = AsyncMock()
        mock_get_monitor.return_value = mock_monitor
        
        await monitor_api_call(
            api_name="test", 
            endpoint="/test", 
            success=True, 
            cost=0.01
        )
        
        # record_api_call 호출 확인
        mock_monitor.record_api_call.assert_called_once_with(
            "test", "/test", True, cost=0.01
        )


# ========== 오래된 데이터 정리 테스트 ==========
@pytest.mark.asyncio
async def test_prune_old_data(api_monitor):
    """오래된 데이터 정리 테스트"""
    # 현재 시간 모킹
    current_time = datetime(2023, 6, 1)
    
    with patch('src.api.api_monitor.datetime') as mock_datetime:
        # 현재 시간 설정
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime
        
        # 100일 전 데이터
        old_hourly = "2023-02-21-10"  # 2월 21일 10시
        old_daily = "2023-02-21"      # 2월 21일
        
        # 10일 전 데이터
        recent_hourly = "2023-05-22-10"  # 5월 22일 10시
        recent_daily = "2023-05-22"      # 5월 22일
        
        # 가짜 데이터 추가
        api_monitor.usage_data["test_api"] = ApiUsageData()
        api_monitor.usage_data["test_api"].hourly_usage = {
            old_hourly: {"calls": 10, "success": 8, "errors": 2, "endpoints": {}},
            recent_hourly: {"calls": 5, "success": 5, "errors": 0, "endpoints": {}}
        }
        api_monitor.usage_data["test_api"].daily_usage = {
            old_daily: {"calls": 100, "success": 90, "errors": 10, "cost": 1.0},
            recent_daily: {"calls": 50, "success": 48, "errors": 2, "cost": 0.5}
        }
        
        # 90일보다 오래된 데이터 정리
        await api_monitor.prune_old_data(older_than_days=90)
        
        # 검증: 오래된 데이터는 삭제되고 최근 데이터는 유지
        assert old_hourly not in api_monitor.usage_data["test_api"].hourly_usage
        assert old_daily not in api_monitor.usage_data["test_api"].daily_usage
        assert recent_hourly in api_monitor.usage_data["test_api"].hourly_usage
        assert recent_daily in api_monitor.usage_data["test_api"].daily_usage 