"""
API 모니터링 예제

이 스크립트는 API 모니터링 기능을 시연하는 예제입니다.
"""
import asyncio
import sys
import os
import random
import time
from pathlib import Path

# 상위 경로를 라이브러리 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.api.api_monitor import get_api_monitor
from src.api.api_client import BaseAPIClient


# 테스트용 모의 API 클라이언트
class MockAPIClient(BaseAPIClient):
    """테스트용 모의 API 클라이언트"""
    
    def __init__(self):
        super().__init__(api_key="mock_key", base_url="https://api.example.com", use_cache=False)
        self.api_type = "mock_api"  # API 유형 설정
    
    async def validate_api_key(self) -> bool:
        """API 키 검증 (항상 성공)"""
        return True
    
    async def simulate_request(self, endpoint: str, success_rate: float = 0.9,
                               tokens: bool = False, sleep: float = 0.2) -> None:
        """
        API 요청을 시뮬레이션합니다.
        
        Args:
            endpoint (str): 엔드포인트
            success_rate (float): 성공 확률 (0.0~1.0)
            tokens (bool): 토큰 정보 포함 여부
            sleep (float): 지연 시간(초)
        """
        # 무작위 데이터 생성
        is_success = random.random() < success_rate
        
        # 토큰 정보 (토큰 포함 옵션이 켜진 경우)
        token_data = None
        if tokens and is_success:
            prompt_tokens = random.randint(10, 100)
            completion_tokens = random.randint(50, 500)
            token_data = {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": prompt_tokens + completion_tokens
            }
        
        # 응답 생성
        response_data = {}
        if is_success:
            response_data = {"result": "Success", "id": f"req_{int(time.time())}"}
            if tokens:
                response_data["usage"] = {
                    "prompt_tokens": token_data["prompt"],
                    "completion_tokens": token_data["completion"],
                    "total_tokens": token_data["total"]
                }
        else:
            response_data = {"error": "Simulated API error"}
        
        # 요청 지연 시뮬레이션
        if sleep > 0:
            await asyncio.sleep(sleep)
        
        # API 요청 수행 (실제로는 모니터링만 함)
        await self.request(
            method="POST",
            endpoint=endpoint,
            data={"dummy": "data"},
            # 모니터링을 위해 모의 응답 데이터 사용
            _mock_response=(is_success, response_data)
        )


# 기존 request 메서드 오버라이드
original_request = BaseAPIClient.request

async def mocked_request(self, method: str, endpoint: str, data=None, 
                         params=None, headers=None, use_cache=None, 
                         check_limits=True, _mock_response=None):
    """
    예제를 위해 모의 응답을 반환하는 요청 메서드
    
    Args:
        ...: 기존 매개변수와 동일
        _mock_response (Tuple[bool, Any], optional): 모의 응답 (테스트용)
    """
    # 모의 응답이 제공된 경우 사용
    if _mock_response is not None:
        success, response_data = _mock_response
        
        # API 사용량 기록
        if self.use_monitor and self.api_monitor:
            # 토큰 정보 추출 (텍스트 API의 경우)
            tokens = None
            if success and isinstance(response_data, dict) and "usage" in response_data:
                tokens = {}
                usage = response_data["usage"]
                if "prompt_tokens" in usage:
                    tokens["prompt"] = usage["prompt_tokens"]
                if "completion_tokens" in usage:
                    tokens["completion"] = usage["completion_tokens"]
                if "total_tokens" in usage:
                    tokens["total"] = usage["total_tokens"]
            
            # API 호출 기록
            await self.api_monitor.record_api_call(
                api_name=self.api_type,
                endpoint=endpoint,
                success=success,
                tokens=tokens,
                duration=random.uniform(0.1, 1.0),  # 무작위 지연
                metadata={
                    "method": method,
                    "params": str(params) if params else None,
                    "data_size": len(str(data)) if data else 0
                }
            )
        
        return success, response_data
    
    # 기존 요청 메서드 호출
    return await original_request(self, method, endpoint, data, params, headers, use_cache, check_limits)

# 요청 메서드 모킹
BaseAPIClient.request = mocked_request


async def run_simulation():
    """API 요청 시뮬레이션 실행"""
    # API 모니터 인스턴스 가져오기
    monitor = get_api_monitor()
    
    # 모의 API 클라이언트 생성
    api_client = MockAPIClient()
    
    # 사용량 제한 설정
    await api_client.set_usage_limit("hourly", 50)
    await api_client.set_cost_info(cost_per_call=0.002, monthly_budget=10.0)
    
    print("API 요청 시뮬레이션 시작...")
    
    # 여러 엔드포인트에 대한 API 요청 시뮬레이션
    endpoints = [
        "/v1/chat/completions",
        "/v1/embeddings",
        "/v1/images/generations"
    ]
    
    # 각 엔드포인트별로 여러 요청 수행
    for i in range(20):
        endpoint = random.choice(endpoints)
        
        # 채팅 완료 엔드포인트는 토큰 정보 포함
        include_tokens = (endpoint == "/v1/chat/completions")
        success_rate = 0.9  # 90% 성공률
        
        # 요청 시뮬레이션
        await api_client.simulate_request(
            endpoint=endpoint,
            success_rate=success_rate,
            tokens=include_tokens,
            sleep=0.1
        )
        
        # 진행 상황 표시
        print(f"요청 {i+1}/20 완료: {endpoint}")
    
    print("\n시뮬레이션 완료!")
    
    # 사용량 통계 조회 및 표시
    stats = await api_client.get_usage_stats()
    
    print("\n=== API 사용량 통계 ===")
    print(f"총 API 호출 수: {stats['total_calls']}")
    print(f"성공한 호출: {stats['success_count']}")
    print(f"실패한 호출: {stats['error_count']}")
    print(f"성공률: {stats['success_rate']:.1f}%")
    
    # 엔드포인트별 통계
    print("\n=== 엔드포인트별 통계 ===")
    this_hour = time.strftime("%Y-%m-%d-%H")
    hourly_usage = stats.get("hourly_usage", {}).get(this_hour, {})
    
    for endpoint, endpoint_stats in hourly_usage.get("endpoints", {}).items():
        print(f"\n엔드포인트: {endpoint}")
        print(f"  호출 수: {endpoint_stats['calls']}")
        print(f"  성공: {endpoint_stats['success']}")
        print(f"  실패: {endpoint_stats['errors']}")
    
    # 토큰 사용량
    tokens = stats.get("tokens", {})
    if tokens:
        print("\n=== 토큰 사용량 ===")
        print(f"프롬프트 토큰: {tokens.get('prompt', 0)}")
        print(f"완료 토큰: {tokens.get('completion', 0)}")
        print(f"총 토큰: {tokens.get('total', 0)}")
    
    print("\n시뮬레이션 및 통계 조회 완료!")
    print("자세한 통계는 'python -m src.utils.api_stats' 명령어로 확인하세요.")


if __name__ == "__main__":
    asyncio.run(run_simulation()) 