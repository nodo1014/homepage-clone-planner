"""
API 사용량 모니터링

이 모듈은 API 호출 횟수 및 비용을 추적하는 기능을 제공합니다.
각 API 별로 사용량 제한을 설정하고 관리할 수 있습니다.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import asyncio
import os

# 로거 설정
logger = logging.getLogger(__name__)

# 기본 모니터링 데이터 저장 경로
DEFAULT_MONITOR_DATA_DIR = Path.home() / ".cloner" / "monitor"


class ApiUsageData:
    """API 사용량 데이터 클래스"""
    
    def __init__(self):
        # 시간대별 사용량 (1시간 단위)
        self.hourly_usage = {}
        # 일별 사용량
        self.daily_usage = {}
        # 월별 사용량
        self.monthly_usage = {}
        # 사용량 제한
        self.limits = {
            "hourly": None,  # 시간당 최대 호출 수
            "daily": None,   # 일별 최대 호출 수
            "monthly": None, # 월별 최대 호출 수
            "total": None    # 총 최대 호출 수
        }
        # 비용 정보
        self.costs = {
            "total_cost": 0.0,      # 총 비용
            "cost_per_call": 0.0,   # 호출당 비용
            "monthly_budget": None  # 월 예산
        }
        # 총 사용량
        self.total_calls = 0
        # 총 토큰 수 (텍스트 API의 경우)
        self.total_tokens = {
            "prompt": 0,
            "completion": 0,
            "total": 0
        }
        # 성공/실패 카운트
        self.success_count = 0
        self.error_count = 0
        # 마지막 업데이트 시간
        self.last_updated = datetime.now().isoformat()
        # API 유형
        self.api_type = ""
        # 모델 정보 (해당되는 경우)
        self.model_info = {}


class ApiMonitor:
    """API 사용량 모니터링 클래스"""
    
    def __init__(
        self, 
        data_dir: Union[str, Path] = DEFAULT_MONITOR_DATA_DIR,
        auto_save: bool = True,
        save_interval: int = 60  # 60초마다 자동 저장
    ):
        """
        API 모니터 초기화
        
        Args:
            data_dir (Union[str, Path]): 사용량 데이터 저장 디렉토리
            auto_save (bool): 자동 저장 활성화 여부
            save_interval (int): 자동 저장 간격(초)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # API별 사용량 데이터
        self.usage_data = {}
        
        # 락 설정 (스레드 안전 보장)
        self._lock = asyncio.Lock()
        
        # 자동 저장 설정
        self.auto_save = auto_save
        self.save_interval = save_interval
        self._last_save_time = time.time()
        
        # 사용량 데이터 로드
        self._load_data()
    
    async def record_api_call(
        self, 
        api_name: str, 
        endpoint: str, 
        success: bool, 
        tokens: Optional[Dict[str, int]] = None,
        cost: Optional[float] = None,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        API 호출 기록
        
        Args:
            api_name (str): API 이름 (예: 'openai', 'claude')
            endpoint (str): 호출된 엔드포인트 (예: '/v1/chat/completions')
            success (bool): 호출 성공 여부
            tokens (Optional[Dict[str, int]]): 사용된 토큰 정보 (텍스트 API의 경우)
            cost (Optional[float]): 호출 비용
            duration (Optional[float]): 호출 소요 시간(초)
            metadata (Optional[Dict[str, Any]]): 추가 메타데이터
        """
        async with self._lock:
            now = datetime.now()
            hour_key = now.strftime("%Y-%m-%d-%H")
            day_key = now.strftime("%Y-%m-%d")
            month_key = now.strftime("%Y-%m")
            
            # API별 사용량 데이터가 없으면 초기화
            if api_name not in self.usage_data:
                self.usage_data[api_name] = ApiUsageData()
                self.usage_data[api_name].api_type = api_name
            
            api_data = self.usage_data[api_name]
            
            # 시간별 사용량 업데이트
            if hour_key not in api_data.hourly_usage:
                api_data.hourly_usage[hour_key] = {
                    "calls": 0, 
                    "success": 0, 
                    "errors": 0,
                    "endpoints": {}
                }
            
            api_data.hourly_usage[hour_key]["calls"] += 1
            if success:
                api_data.hourly_usage[hour_key]["success"] += 1
            else:
                api_data.hourly_usage[hour_key]["errors"] += 1
            
            # 엔드포인트별 사용량
            if endpoint not in api_data.hourly_usage[hour_key]["endpoints"]:
                api_data.hourly_usage[hour_key]["endpoints"][endpoint] = {
                    "calls": 0, 
                    "success": 0, 
                    "errors": 0
                }
            
            api_data.hourly_usage[hour_key]["endpoints"][endpoint]["calls"] += 1
            if success:
                api_data.hourly_usage[hour_key]["endpoints"][endpoint]["success"] += 1
            else:
                api_data.hourly_usage[hour_key]["endpoints"][endpoint]["errors"] += 1
            
            # 일별 사용량 업데이트
            if day_key not in api_data.daily_usage:
                api_data.daily_usage[day_key] = {
                    "calls": 0, 
                    "success": 0, 
                    "errors": 0, 
                    "cost": 0.0
                }
            
            api_data.daily_usage[day_key]["calls"] += 1
            if success:
                api_data.daily_usage[day_key]["success"] += 1
            else:
                api_data.daily_usage[day_key]["errors"] += 1
            
            # 월별 사용량 업데이트
            if month_key not in api_data.monthly_usage:
                api_data.monthly_usage[month_key] = {
                    "calls": 0, 
                    "success": 0, 
                    "errors": 0, 
                    "cost": 0.0, 
                    "tokens": {"prompt": 0, "completion": 0, "total": 0}
                }
            
            api_data.monthly_usage[month_key]["calls"] += 1
            if success:
                api_data.monthly_usage[month_key]["success"] += 1
            else:
                api_data.monthly_usage[month_key]["errors"] += 1
            
            # 토큰 정보 업데이트
            if tokens:
                if "prompt" in tokens:
                    api_data.total_tokens["prompt"] += tokens["prompt"]
                    api_data.monthly_usage[month_key]["tokens"]["prompt"] += tokens["prompt"]
                
                if "completion" in tokens:
                    api_data.total_tokens["completion"] += tokens["completion"]
                    api_data.monthly_usage[month_key]["tokens"]["completion"] += tokens["completion"]
                
                if "total" in tokens:
                    api_data.total_tokens["total"] += tokens["total"]
                    api_data.monthly_usage[month_key]["tokens"]["total"] += tokens["total"]
                elif "prompt" in tokens and "completion" in tokens:
                    total = tokens["prompt"] + tokens["completion"]
                    api_data.total_tokens["total"] += total
                    api_data.monthly_usage[month_key]["tokens"]["total"] += total
            
            # 비용 업데이트
            if cost:
                api_data.costs["total_cost"] += cost
                api_data.daily_usage[day_key]["cost"] += cost
                api_data.monthly_usage[month_key]["cost"] += cost
            
            # 총 호출 카운트 업데이트
            api_data.total_calls += 1
            if success:
                api_data.success_count += 1
            else:
                api_data.error_count += 1
            
            # 마지막 업데이트 시간
            api_data.last_updated = now.isoformat()
            
            # 메타데이터 저장 (선택 사항)
            if metadata:
                # 메타데이터를 저장할 구조가 없다면 생성
                if not hasattr(api_data, "metadata"):
                    api_data.metadata = {}
                
                # 최근 호출 메타데이터 업데이트
                api_data.metadata["last_call"] = {
                    "time": now.isoformat(),
                    "endpoint": endpoint,
                    "success": success,
                    "duration": duration,
                    **metadata
                }
            
            # 자동 저장 처리
            if self.auto_save and (time.time() - self._last_save_time) > self.save_interval:
                await self.save_data()
    
    async def check_limits(self, api_name: str) -> Tuple[bool, Optional[str]]:
        """
        API 사용량 제한 확인
        
        Args:
            api_name (str): API 이름
            
        Returns:
            Tuple[bool, Optional[str]]: (제한 초과 여부, 초과된 제한 유형)
        """
        async with self._lock:
            if api_name not in self.usage_data:
                return False, None
            
            api_data = self.usage_data[api_name]
            now = datetime.now()
            
            # 시간당 제한 확인
            if api_data.limits["hourly"] is not None:
                hour_key = now.strftime("%Y-%m-%d-%H")
                if hour_key in api_data.hourly_usage:
                    hourly_calls = api_data.hourly_usage[hour_key]["calls"]
                    if hourly_calls >= api_data.limits["hourly"]:
                        return True, "hourly"
            
            # 일별 제한 확인
            if api_data.limits["daily"] is not None:
                day_key = now.strftime("%Y-%m-%d")
                if day_key in api_data.daily_usage:
                    daily_calls = api_data.daily_usage[day_key]["calls"]
                    if daily_calls >= api_data.limits["daily"]:
                        return True, "daily"
            
            # 월별 제한 확인
            if api_data.limits["monthly"] is not None:
                month_key = now.strftime("%Y-%m")
                if month_key in api_data.monthly_usage:
                    monthly_calls = api_data.monthly_usage[month_key]["calls"]
                    if monthly_calls >= api_data.limits["monthly"]:
                        return True, "monthly"
            
            # 총 제한 확인
            if api_data.limits["total"] is not None:
                if api_data.total_calls >= api_data.limits["total"]:
                    return True, "total"
            
            # 월별 예산 제한 확인
            if api_data.costs["monthly_budget"] is not None:
                month_key = now.strftime("%Y-%m")
                if month_key in api_data.monthly_usage:
                    monthly_cost = api_data.monthly_usage[month_key]["cost"]
                    if monthly_cost >= api_data.costs["monthly_budget"]:
                        return True, "budget"
            
            return False, None
    
    async def set_limit(
        self, 
        api_name: str, 
        limit_type: str, 
        value: Optional[int]
    ) -> None:
        """
        API 사용량 제한 설정
        
        Args:
            api_name (str): API 이름
            limit_type (str): 제한 유형 ('hourly', 'daily', 'monthly', 'total')
            value (Optional[int]): 제한 값 (None은 제한 없음)
        """
        async with self._lock:
            if api_name not in self.usage_data:
                self.usage_data[api_name] = ApiUsageData()
                self.usage_data[api_name].api_type = api_name
            
            if limit_type in self.usage_data[api_name].limits:
                self.usage_data[api_name].limits[limit_type] = value
                logger.info(f"{api_name}의 {limit_type} 제한이 {value}로 설정되었습니다.")
            
            await self.save_data()
    
    async def set_cost_info(
        self, 
        api_name: str, 
        cost_per_call: Optional[float] = None,
        monthly_budget: Optional[float] = None
    ) -> None:
        """
        API 비용 정보 설정
        
        Args:
            api_name (str): API 이름
            cost_per_call (Optional[float]): 호출당 비용
            monthly_budget (Optional[float]): 월 예산
        """
        async with self._lock:
            if api_name not in self.usage_data:
                self.usage_data[api_name] = ApiUsageData()
                self.usage_data[api_name].api_type = api_name
            
            if cost_per_call is not None:
                self.usage_data[api_name].costs["cost_per_call"] = cost_per_call
            
            if monthly_budget is not None:
                self.usage_data[api_name].costs["monthly_budget"] = monthly_budget
            
            await self.save_data()
    
    async def get_usage_stats(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """
        API 사용량 통계 조회
        
        Args:
            api_name (Optional[str]): API 이름 (None이면 전체)
            
        Returns:
            Dict[str, Any]: 사용량 통계 정보
        """
        async with self._lock:
            if api_name:
                if api_name not in self.usage_data:
                    return {}
                
                return self._get_api_stats(api_name)
            else:
                # 전체 API 통계
                stats = {}
                for name in self.usage_data:
                    stats[name] = self._get_api_stats(name)
                
                # 전체 요약 추가
                total_calls = sum(data.total_calls for data in self.usage_data.values())
                total_success = sum(data.success_count for data in self.usage_data.values())
                total_errors = sum(data.error_count for data in self.usage_data.values())
                total_cost = sum(data.costs["total_cost"] for data in self.usage_data.values())
                
                stats["_summary"] = {
                    "total_calls": total_calls,
                    "success_count": total_success,
                    "error_count": total_errors,
                    "success_rate": (total_success / total_calls * 100) if total_calls > 0 else 0,
                    "total_cost": total_cost
                }
                
                return stats
    
    def _get_api_stats(self, api_name: str) -> Dict[str, Any]:
        """
        특정 API의 통계 정보 조회 (내부 사용)
        
        Args:
            api_name (str): API 이름
            
        Returns:
            Dict[str, Any]: 통계 정보
        """
        api_data = self.usage_data[api_name]
        now = datetime.now()
        
        # 오늘 사용량
        today_key = now.strftime("%Y-%m-%d")
        today_calls = 0
        today_cost = 0.0
        if today_key in api_data.daily_usage:
            today_calls = api_data.daily_usage[today_key]["calls"]
            today_cost = api_data.daily_usage[today_key]["cost"]
        
        # 이번 달 사용량
        month_key = now.strftime("%Y-%m")
        month_calls = 0
        month_cost = 0.0
        if month_key in api_data.monthly_usage:
            month_calls = api_data.monthly_usage[month_key]["calls"]
            month_cost = api_data.monthly_usage[month_key]["cost"]
        
        # 통계 생성
        stats = {
            "total_calls": api_data.total_calls,
            "success_count": api_data.success_count,
            "error_count": api_data.error_count,
            "success_rate": (api_data.success_count / api_data.total_calls * 100) if api_data.total_calls > 0 else 0,
            "total_cost": api_data.costs["total_cost"],
            "today": {
                "calls": today_calls,
                "cost": today_cost
            },
            "this_month": {
                "calls": month_calls,
                "cost": month_cost,
                "budget": api_data.costs["monthly_budget"],
                "budget_used_percent": (month_cost / api_data.costs["monthly_budget"] * 100) if api_data.costs["monthly_budget"] else 0
            },
            "limits": api_data.limits,
            "tokens": api_data.total_tokens if hasattr(api_data, "total_tokens") else None,
            "last_updated": api_data.last_updated
        }
        
        return stats
    
    async def clear_usage_data(self, api_name: Optional[str] = None) -> None:
        """
        사용량 데이터 초기화
        
        Args:
            api_name (Optional[str]): API 이름 (None이면 전체)
        """
        async with self._lock:
            if api_name:
                if api_name in self.usage_data:
                    # 제한 설정 저장
                    limits = self.usage_data[api_name].limits
                    costs = self.usage_data[api_name].costs
                    
                    # 데이터 초기화
                    self.usage_data[api_name] = ApiUsageData()
                    self.usage_data[api_name].api_type = api_name
                    
                    # 제한 복원
                    self.usage_data[api_name].limits = limits
                    self.usage_data[api_name].costs = costs
            else:
                # 전체 초기화
                for name in list(self.usage_data.keys()):
                    # 제한 설정 저장
                    limits = self.usage_data[name].limits
                    costs = self.usage_data[name].costs
                    
                    # 데이터 초기화
                    self.usage_data[name] = ApiUsageData()
                    self.usage_data[name].api_type = name
                    
                    # 제한 복원
                    self.usage_data[name].limits = limits
                    self.usage_data[name].costs = costs
            
            await self.save_data()
    
    async def save_data(self) -> None:
        """모니터링 데이터를 파일에 저장"""
        async with self._lock:
            try:
                for api_name, api_data in self.usage_data.items():
                    # API별 데이터 파일
                    data_file = self.data_dir / f"{api_name}_usage.json"
                    
                    # 데이터를 딕셔너리로 변환
                    data_dict = {
                        "hourly_usage": api_data.hourly_usage,
                        "daily_usage": api_data.daily_usage,
                        "monthly_usage": api_data.monthly_usage,
                        "limits": api_data.limits,
                        "costs": api_data.costs,
                        "total_calls": api_data.total_calls,
                        "success_count": api_data.success_count,
                        "error_count": api_data.error_count,
                        "total_tokens": api_data.total_tokens,
                        "last_updated": api_data.last_updated,
                        "api_type": api_data.api_type
                    }
                    
                    # 메타데이터가 있는 경우 추가
                    if hasattr(api_data, "metadata"):
                        data_dict["metadata"] = api_data.metadata
                    
                    # 파일에 저장
                    with open(data_file, "w") as f:
                        json.dump(data_dict, f, indent=2)
                
                self._last_save_time = time.time()
                logger.debug("API 사용량 데이터가 저장되었습니다.")
            except Exception as e:
                logger.error(f"API 사용량 데이터 저장 중 오류 발생: {str(e)}")
    
    def _load_data(self) -> None:
        """저장된 모니터링 데이터 로드"""
        try:
            # 저장 디렉토리의 모든 데이터 파일 확인
            for data_file in self.data_dir.glob("*_usage.json"):
                try:
                    with open(data_file, "r") as f:
                        data_dict = json.load(f)
                    
                    # 파일 이름에서 API 이름 추출
                    api_name = data_file.stem.replace("_usage", "")
                    
                    # ApiUsageData 객체 생성 및 데이터 로드
                    api_data = ApiUsageData()
                    api_data.hourly_usage = data_dict.get("hourly_usage", {})
                    api_data.daily_usage = data_dict.get("daily_usage", {})
                    api_data.monthly_usage = data_dict.get("monthly_usage", {})
                    api_data.limits = data_dict.get("limits", {})
                    api_data.costs = data_dict.get("costs", {})
                    api_data.total_calls = data_dict.get("total_calls", 0)
                    api_data.success_count = data_dict.get("success_count", 0)
                    api_data.error_count = data_dict.get("error_count", 0)
                    api_data.total_tokens = data_dict.get("total_tokens", {"prompt": 0, "completion": 0, "total": 0})
                    api_data.last_updated = data_dict.get("last_updated", datetime.now().isoformat())
                    api_data.api_type = data_dict.get("api_type", api_name)
                    
                    # 메타데이터가 있는 경우 로드
                    if "metadata" in data_dict:
                        api_data.metadata = data_dict["metadata"]
                    
                    # 데이터 저장
                    self.usage_data[api_name] = api_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"데이터 파일 파싱 실패 ({data_file}): {str(e)}")
                except Exception as e:
                    logger.error(f"데이터 파일 로드 중 오류 ({data_file}): {str(e)}")
            
            logger.info(f"{len(self.usage_data)}개의 API 사용량 데이터를 로드했습니다.")
        except Exception as e:
            logger.error(f"API 사용량 데이터 로드 중 오류 발생: {str(e)}")
    
    async def prune_old_data(self, older_than_days: int = 90) -> None:
        """
        오래된 사용량 데이터 정리
        
        Args:
            older_than_days (int): 이 일수보다 오래된 데이터 삭제 (기본값: 90일)
        """
        async with self._lock:
            try:
                cutoff_date = datetime.now() - timedelta(days=older_than_days)
                
                for api_name, api_data in self.usage_data.items():
                    # 시간별 데이터 정리
                    hourly_keys = list(api_data.hourly_usage.keys())
                    for hour_key in hourly_keys:
                        try:
                            # 키 형식: "YYYY-MM-DD-HH"
                            hour_date = datetime.strptime(hour_key, "%Y-%m-%d-%H")
                            if hour_date < cutoff_date:
                                del api_data.hourly_usage[hour_key]
                        except ValueError:
                            # 날짜 파싱 오류 - 키가 잘못된 형식일 수 있음
                            pass
                    
                    # 일별 데이터 정리
                    daily_keys = list(api_data.daily_usage.keys())
                    for day_key in daily_keys:
                        try:
                            # 키 형식: "YYYY-MM-DD"
                            day_date = datetime.strptime(day_key, "%Y-%m-%d")
                            if day_date < cutoff_date:
                                del api_data.daily_usage[day_key]
                        except ValueError:
                            pass
                
                await self.save_data()
                logger.info(f"{older_than_days}일보다 오래된 사용량 데이터가 정리되었습니다.")
            except Exception as e:
                logger.error(f"데이터 정리 중 오류 발생: {str(e)}")


class ApiMonitorDecorator:
    """API 모니터링 데코레이터"""
    
    def __init__(
        self, 
        api_monitor: ApiMonitor, 
        api_name: str,
        check_limits: bool = True
    ):
        """
        API 모니터링 데코레이터 초기화
        
        Args:
            api_monitor (ApiMonitor): API 모니터 인스턴스
            api_name (str): API 이름
            check_limits (bool): 제한 확인 여부
        """
        self.api_monitor = api_monitor
        self.api_name = api_name
        self.check_limits = check_limits
    
    def __call__(self, func):
        """
        데코레이터 적용
        
        Args:
            func: 장식할 함수
            
        Returns:
            Callable: 장식된 함수
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # API 제한 확인
            if self.check_limits:
                limit_exceeded, limit_type = await self.api_monitor.check_limits(self.api_name)
                if limit_exceeded:
                    limit_error = {
                        "error": f"API 사용량 제한 초과: {limit_type}",
                        "details": f"{self.api_name} API의 {limit_type} 사용량 제한이 초과되었습니다."
                    }
                    logger.warning(f"{self.api_name} API 사용량 제한 초과: {limit_type}")
                    return False, limit_error
            
            # 시작 시간 기록
            start_time = time.time()
            
            # 함수 실행
            try:
                result = await func(*args, **kwargs)
                success, data = result
                
                # 토큰 정보 추출 (텍스트 API의 경우)
                tokens = None
                if success and isinstance(data, dict) and "usage" in data:
                    tokens = {}
                    usage = data["usage"]
                    if "prompt_tokens" in usage:
                        tokens["prompt"] = usage["prompt_tokens"]
                    if "completion_tokens" in usage:
                        tokens["completion"] = usage["completion_tokens"]
                    if "total_tokens" in usage:
                        tokens["total"] = usage["total_tokens"]
                
                # 비용 계산 (호출 시 설정된 비용 정보 사용)
                cost = None
                # 여기에 필요한 경우 API별 비용 계산 로직을 추가
                
                # 호출 기록
                duration = time.time() - start_time
                endpoint = kwargs.get("endpoint", "unknown")
                
                # API 호출 결과 기록
                await self.api_monitor.record_api_call(
                    api_name=self.api_name,
                    endpoint=endpoint,
                    success=success,
                    tokens=tokens,
                    cost=cost,
                    duration=duration,
                    metadata={"args": str(args), "kwargs": str(kwargs)}
                )
                
                return result
            
            except Exception as e:
                # 예외 발생 시에도 기록
                duration = time.time() - start_time
                await self.api_monitor.record_api_call(
                    api_name=self.api_name,
                    endpoint=kwargs.get("endpoint", "unknown"),
                    success=False,
                    duration=duration,
                    metadata={"error": str(e)}
                )
                
                # 예외 다시 발생
                raise
        
        return wrapper


# 전역 API 모니터 인스턴스
_api_monitor = None

def get_api_monitor() -> ApiMonitor:
    """
    전역 API 모니터 인스턴스를 반환합니다.
    
    Returns:
        ApiMonitor: API 모니터 인스턴스
    """
    global _api_monitor
    if _api_monitor is None:
        _api_monitor = ApiMonitor()
    
    return _api_monitor

async def monitor_api_call(api_name: str, endpoint: str, success: bool, **kwargs) -> None:
    """
    API 호출을 모니터링합니다.
    
    Args:
        api_name (str): API 이름
        endpoint (str): 엔드포인트
        success (bool): 성공 여부
        **kwargs: 추가 매개변수
    """
    monitor = get_api_monitor()
    await monitor.record_api_call(api_name, endpoint, success, **kwargs)

# 함수 래핑에 필요한 메타 정보
from functools import wraps 