"""
외부 API 클라이언트

이 모듈은 외부 API(OpenAI, DeepSeek, Claude 등)와 통신하는 기능을 제공합니다.
"""
import logging
import os
import json
import httpx
from typing import Dict, Any, List, Tuple, Optional, Callable, Union
import asyncio
from src.utils.retry import RetryConfig, async_retry, DEFAULT_RETRY_EXCEPTIONS
from src.utils.cache import CacheManager, cached_api_response, LRUCache, DiskCache
from src.api.api_monitor import ApiMonitor, get_api_monitor

# 로깅 설정
logger = logging.getLogger(__name__)

# API 요청 시 재시도할 HTTP 상태 코드
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# 기본 캐시 설정
DEFAULT_API_CACHE_TTL = 3600 * 24  # 24시간
DEFAULT_API_MEMORY_CACHE_SIZE = 100
DEFAULT_API_DISK_CACHE_SIZE = 1000


class BaseAPIClient:
    """기본 API 클라이언트 클래스"""
    
    def __init__(self, api_key: str = None, base_url: str = None, use_cache: bool = True, use_monitor: bool = True):
        """
        기본 API 클라이언트 초기화
        
        Args:
            api_key (str, optional): API 키
            base_url (str, optional): API 기본 URL
            use_cache (bool, optional): 캐싱 사용 여부
            use_monitor (bool, optional): API 사용량 모니터링 사용 여부
        """
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.use_cache = use_cache
        self.use_monitor = use_monitor
        
        # API 타입 (하위 클래스에서 재정의해야 함)
        self.api_type = self.__class__.__name__.lower()
        
        # 기본 재시도 설정
        self.retry_config = RetryConfig(
            retry_count=3,
            base_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            retry_exceptions=(*DEFAULT_RETRY_EXCEPTIONS, httpx.HTTPStatusError, httpx.RequestError),
            retry_on_result=self._should_retry_on_result
        )
        
        # 캐시 설정
        if use_cache:
            # 클라이언트별 고유한 캐시 프리픽스 생성
            cache_prefix = self.__class__.__name__.lower()
            
            # 메모리 캐시 및 디스크 캐시 생성
            memory_cache = LRUCache(
                max_size=DEFAULT_API_MEMORY_CACHE_SIZE,
                ttl=DEFAULT_API_CACHE_TTL
            )
            
            disk_cache = DiskCache(
                max_size=DEFAULT_API_DISK_CACHE_SIZE,
                ttl=DEFAULT_API_CACHE_TTL
            )
            
            # 캐시 관리자 생성
            self.cache_manager = CacheManager(
                memory_cache=memory_cache,
                disk_cache=disk_cache
            )
        else:
            self.cache_manager = None
        
        # API 모니터 설정
        if use_monitor:
            self.api_monitor = get_api_monitor()
        else:
            self.api_monitor = None
    
    def _should_retry_on_result(self, result: Tuple[bool, Any]) -> bool:
        """
        결과를 기반으로 재시도 여부를 결정합니다.
        
        Args:
            result (Tuple[bool, Any]): request 메서드의 반환값 (success, data)
        
        Returns:
            bool: 재시도 여부
        """
        success, data = result
        
        # 성공한 경우 재시도 안 함
        if success:
            return False
        
        # 오류 데이터에 HTTP 상태 코드가 있는지 확인
        if isinstance(data, dict) and 'status_code' in data:
            status_code = data['status_code']
            logger.debug(f"상태 코드 {status_code}에 대한 재시도 여부 검사")
            return status_code in RETRYABLE_STATUS_CODES
        
        # 오류 데이터에 재시도 가능한 메시지가 있는지 확인
        if isinstance(data, dict) and 'error' in data:
            error_msg = str(data['error']).lower()
            should_retry = (
                'timeout' in error_msg or
                'rate limit' in error_msg or
                'too many requests' in error_msg or
                'server error' in error_msg or
                'service unavailable' in error_msg or
                'network' in error_msg or
                'connection' in error_msg
            )
            logger.debug(f"오류 메시지 '{error_msg}'에 대한 재시도 여부: {should_retry}")
            return should_retry
        
        return False
    
    async def close(self):
        """
        클라이언트 연결 종료
        """
        await self.client.aclose()
    
    async def _request_impl(self, method: str, endpoint: str, data: Dict[str, Any] = None, 
                      params: Dict[str, Any] = None, headers: Dict[str, Any] = None) -> Tuple[bool, Any]:
        """
        API 요청 구현 (내부 사용)
        
        Args:
            method (str): HTTP 메서드 (GET, POST 등)
            endpoint (str): API 엔드포인트
            data (Dict[str, Any], optional): 요청 본문 데이터
            params (Dict[str, Any], optional): URL 쿼리 파라미터
            headers (Dict[str, Any], optional): HTTP 헤더
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 응답 데이터 또는 오류 메시지)
        """
        if headers is None:
            headers = {}
        
        # API 키가 있는 경우 인증 헤더 추가
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        url = f"{self.base_url}{endpoint}" if self.base_url else endpoint
        
        try:
            response = await self.client.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers
            )
            
            # 응답 검사
            response.raise_for_status()
            
            # JSON 응답인 경우 파싱
            if "application/json" in response.headers.get("Content-Type", ""):
                return True, response.json()
            
            # 그 외의 경우 텍스트 반환
            return True, response.text
        
        except httpx.HTTPStatusError as e:
            logger.error(f"API 요청 실패 (HTTP {e.response.status_code}): {str(e)}")
            
            # 오류 응답이 JSON인 경우 파싱
            try:
                error_data = e.response.json()
                error_data['status_code'] = e.response.status_code
                return False, error_data
            except:
                return False, {
                    "error": f"API 요청 실패: HTTP {e.response.status_code}", 
                    "details": str(e),
                    "status_code": e.response.status_code
                }
        
        except httpx.RequestError as e:
            logger.error(f"API 요청 실패 (네트워크 오류): {str(e)}")
            return False, {"error": "네트워크 오류", "details": str(e)}
        
        except Exception as e:
            logger.error(f"API 요청 중 오류 발생: {str(e)}")
            return False, {"error": "API 요청 중 오류 발생", "details": str(e)}
    
    async def request(self, method: str, endpoint: str, data: Dict[str, Any] = None, 
                      params: Dict[str, Any] = None, headers: Dict[str, Any] = None,
                      use_cache: bool = None, check_limits: bool = True) -> Tuple[bool, Any]:
        """
        재시도 로직이 적용된 API 요청 전송
        
        Args:
            method (str): HTTP 메서드 (GET, POST 등)
            endpoint (str): API 엔드포인트
            data (Dict[str, Any], optional): 요청 본문 데이터
            params (Dict[str, Any], optional): URL 쿼리 파라미터
            headers (Dict[str, Any], optional): HTTP 헤더
            use_cache (bool, optional): 캐싱 사용 여부 (None이면 인스턴스 기본값 사용)
            check_limits (bool, optional): API 사용량 제한 확인 여부
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 응답 데이터 또는 오류 메시지)
        """
        # API 사용량 제한 확인
        if self.use_monitor and self.api_monitor and check_limits:
            limit_exceeded, limit_type = await self.api_monitor.check_limits(self.api_type)
            if limit_exceeded:
                error_msg = f"API 사용량 제한 초과: {limit_type}"
                logger.warning(f"{self.api_type} {error_msg}")
                return False, {
                    "error": error_msg,
                    "details": f"{self.api_type} API의 {limit_type} 사용량 제한이 초과되었습니다."
                }
        
        # 캐싱 사용 여부 결정
        should_use_cache = self.use_cache if use_cache is None else use_cache
        
        # 시작 시간 기록 (모니터링용)
        start_time = asyncio.get_event_loop().time()
        
        try:
            # GET 요청이고 캐싱이 활성화되어 있을 때만 캐싱 적용
            if should_use_cache and method.upper() == "GET" and self.cache_manager is not None:
                result = await self._cached_request(method, endpoint, data, params, headers)
            else:
                # 캐싱을 사용하지 않는 경우 직접 요청
                result = await self._direct_request(method, endpoint, data, params, headers)
            
            # API 사용량 기록
            if self.use_monitor and self.api_monitor:
                success, response_data = result
                
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
                
                # 소요 시간 계산
                duration = asyncio.get_event_loop().time() - start_time
                
                # API 호출 기록
                await self.api_monitor.record_api_call(
                    api_name=self.api_type,
                    endpoint=endpoint,
                    success=success,
                    tokens=tokens,
                    duration=duration,
                    metadata={
                        "method": method,
                        "params": str(params) if params else None,
                        "data_size": len(str(data)) if data else 0
                    }
                )
            
            return result
            
        except Exception as e:
            # 예외 발생 시에도 API 사용량 기록
            if self.use_monitor and self.api_monitor:
                duration = asyncio.get_event_loop().time() - start_time
                await self.api_monitor.record_api_call(
                    api_name=self.api_type,
                    endpoint=endpoint,
                    success=False,
                    duration=duration,
                    metadata={"error": str(e)}
                )
            
            # 예외 다시 발생
            raise
    
    async def _cached_request(self, method: str, endpoint: str, data: Dict[str, Any] = None, 
                            params: Dict[str, Any] = None, headers: Dict[str, Any] = None) -> Tuple[bool, Any]:
        """
        캐싱이 적용된 API 요청
        
        Args:
            (request 메소드와 동일)
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 캐시된 응답 데이터 또는 오류 메시지)
        """
        # 캐시 키 생성
        cache_key = self._build_cache_key(method, endpoint, params)
        
        # 캐시에서 조회
        hit, cached_result = await self.cache_manager.get(cache_key)
        if hit:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached_result
        
        # 캐시 미스: 요청 실행
        logger.debug(f"캐시 미스: {cache_key}")
        result = await self._direct_request(method, endpoint, data, params, headers)
        
        # 성공적인 응답만 캐싱
        success, _ = result
        if success:
            await self.cache_manager.set(cache_key, result)
            logger.debug(f"응답 캐싱: {cache_key}")
        
        return result
    
    async def _direct_request(self, method: str, endpoint: str, data: Dict[str, Any] = None, 
                            params: Dict[str, Any] = None, headers: Dict[str, Any] = None) -> Tuple[bool, Any]:
        """
        재시도 메커니즘이 적용된 직접 API 요청
        
        Args:
            (request 메소드와 동일)
            
        Returns:
            Tuple[bool, Any]: (성공 여부, 응답 데이터 또는 오류 메시지)
        """
        # 이 함수는 재시도 메커니즘을 적용할 함수의 인자를 래핑하여 호출
        async def _execute_request():
            return await self._request_impl(
                method=method,
                endpoint=endpoint,
                data=data,
                params=params,
                headers=headers
            )
        
        # 래핑된 함수를 사용하여 재시도 메커니즘 적용
        return await self.retry_config.retry(
            _execute_request
        )
    
    def _build_cache_key(self, method: str, endpoint: str, params: Dict[str, Any] = None) -> str:
        """
        요청에 대한 캐시 키를 생성합니다.
        
        Args:
            method (str): HTTP 메서드
            endpoint (str): API 엔드포인트
            params (Dict[str, Any], optional): URL 쿼리 파라미터
            
        Returns:
            str: 캐시 키
        """
        # 기본 키 생성
        key_parts = [
            self.__class__.__name__,
            method.upper(),
            endpoint
        ]
        
        # URL 파라미터가 있으면 정렬된 키-값 쌍 추가
        if params:
            # 정렬된 파라미터 문자열 생성
            sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            key_parts.append(sorted_params)
        
        # 부분들을 결합하여 최종 키 생성
        return ":".join(key_parts)
    
    def set_retry_config(self, 
                        retry_count: int = None, 
                        base_delay: float = None, 
                        max_delay: float = None,
                        backoff_factor: float = None) -> None:
        """
        재시도 설정을 업데이트합니다.
        
        Args:
            retry_count (int, optional): 최대 재시도 횟수
            base_delay (float, optional): 초기 지연 시간(초)
            max_delay (float, optional): 최대 지연 시간(초)
            backoff_factor (float, optional): 지수 백오프 계수
        """
        if retry_count is not None:
            self.retry_config.retry_count = retry_count
        if base_delay is not None:
            self.retry_config.base_delay = base_delay
        if max_delay is not None:
            self.retry_config.max_delay = max_delay
        if backoff_factor is not None:
            self.retry_config.backoff_factor = backoff_factor
    
    async def validate_api_key(self) -> bool:
        """
        API 키 유효성 검증
        
        Returns:
            bool: API 키 유효 여부
        """
        # 이 메서드는 하위 클래스에서 구현해야 함
        raise NotImplementedError("이 메서드는 하위 클래스에서 구현해야 합니다")
    
    async def clear_cache(self) -> None:
        """
        모든 캐시를 비웁니다.
        """
        if self.use_cache and self.cache_manager is not None:
            await self.cache_manager.clear()
            logger.info(f"{self.__class__.__name__}의 모든 캐시가 지워졌습니다.")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        if self.use_cache and self.cache_manager is not None:
            return await self.cache_manager.get_stats()
        else:
            return {"enabled": False}
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        API 사용량 통계 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 사용량 통계 정보
        """
        if self.use_monitor and self.api_monitor is not None:
            return await self.api_monitor.get_usage_stats(self.api_type)
        else:
            return {"enabled": False}
    
    async def set_usage_limit(self, limit_type: str, value: Optional[int]) -> None:
        """
        API 사용량 제한을 설정합니다.
        
        Args:
            limit_type (str): 제한 유형 ('hourly', 'daily', 'monthly', 'total')
            value (Optional[int]): 제한 값 (None은 제한 없음)
        """
        if self.use_monitor and self.api_monitor is not None:
            await self.api_monitor.set_limit(self.api_type, limit_type, value)
            logger.info(f"{self.api_type}의 {limit_type} 제한이 {value}로 설정되었습니다.")
    
    async def set_cost_info(self, cost_per_call: Optional[float] = None, monthly_budget: Optional[float] = None) -> None:
        """
        API 비용 정보를 설정합니다.
        
        Args:
            cost_per_call (Optional[float]): 호출당 비용
            monthly_budget (Optional[float]): 월별 예산
        """
        if self.use_monitor and self.api_monitor is not None:
            await self.api_monitor.set_cost_info(
                self.api_type, 
                cost_per_call=cost_per_call, 
                monthly_budget=monthly_budget
            )
            logger.info(f"{self.api_type}의 비용 정보가 업데이트되었습니다.")
    
    async def clear_usage_data(self) -> None:
        """
        API 사용량 데이터를 초기화합니다.
        (제한 설정은 유지됩니다)
        """
        if self.use_monitor and self.api_monitor is not None:
            await self.api_monitor.clear_usage_data(self.api_type)
            logger.info(f"{self.api_type}의 사용량 데이터가 초기화되었습니다.")


# API 클라이언트 팩토리
def create_api_client(api_type: str, config: Dict[str, Any]) -> BaseAPIClient:
    """
    API 클라이언트 생성
    
    Args:
        api_type (str): API 유형 (openai, anthropic, ollama, stable_diffusion 등)
        config (Dict[str, Any]): API 설정
        
    Returns:
        BaseAPIClient: API 클라이언트 인스턴스
    """
    try:
        # 캐싱 설정 추출
        use_cache = config.get("api", {}).get("use_cache", True)
        
        # api_type에 따라 적절한 클라이언트 가져오기
        if api_type == "openai":
            from src.api.openai_client import OpenAIClient
            api_key = config.get("api_keys", {}).get("dalle")
            return OpenAIClient(api_key=api_key, use_cache=use_cache)
            
        elif api_type == "anthropic":
            from src.api.anthropic_client import ClaudeClient
            api_key = config.get("api_keys", {}).get("claude")
            return ClaudeClient(api_key=api_key, use_cache=use_cache)
            
        elif api_type == "ollama":
            from src.api.ollama_client import OllamaClient
            api_url = config.get("api", {}).get("local_ollama_url")
            return OllamaClient(api_url=api_url, use_cache=use_cache)
            
        elif api_type == "stable_diffusion":
            from src.api.stable_diffusion_client import StableDiffusionClient
            api_url = config.get("api", {}).get("local_sd_url")
            return StableDiffusionClient(api_url=api_url, use_cache=use_cache)
            
        else:
            logger.error(f"알 수 없는 API 유형: {api_type}")
            return BaseAPIClient(use_cache=use_cache)
            
    except ImportError as e:
        logger.error(f"API 클라이언트 모듈 로드 실패: {str(e)}")
        return BaseAPIClient()
    except Exception as e:
        logger.error(f"API 클라이언트 생성 중 오류 발생: {str(e)}")
        return BaseAPIClient()

# API 클라이언트 팩토리 (모드 기반)
async def create_api_client_by_mode(mode: str, api_type: str, config: Dict[str, Any]) -> BaseAPIClient:
    """
    모드에 따라 API 클라이언트 생성
    
    Args:
        mode (str): API 모드 (free 또는 paid)
        api_type (str): API 종류 (image_gen, idea_gen, code_gen)
        config (Dict[str, Any]): 설정 정보
        
    Returns:
        BaseAPIClient: API 클라이언트 인스턴스
    """
    # 필요한 클래스 임포트
    from src.api.stable_diffusion_client import StableDiffusionClient
    from src.api.ollama_client import OllamaClient
    
    api_config = config.get("api", {})
    
    # 캐싱 설정 추출
    use_cache = api_config.get("use_cache", True)
    
    # 이미지 생성 클라이언트
    if api_type == "image_gen":
        if mode == "paid" or api_config.get("image_gen_mode") == "paid":
            # 유료 API: DALL-E
            client = create_api_client("openai", config)
        else:
            # 무료 API: Stable Diffusion
            client = create_api_client("stable_diffusion", config)
    
    # 아이디어 생성 클라이언트
    elif api_type == "idea_gen":
        if mode == "paid" or api_config.get("idea_gen_mode") == "paid":
            # 유료 API: Claude
            client = create_api_client("anthropic", config)
        else:
            # 무료 API: Ollama
            client = create_api_client("ollama", config)
    
    # 코드 생성 클라이언트
    elif api_type == "code_gen":
        if mode == "paid" or api_config.get("code_gen_mode") == "paid":
            # 유료 API: OpenAI
            client = create_api_client("openai", config)
        else:
            # 무료 API: Ollama
            client = create_api_client("ollama", config)
    
    else:
        logger.error(f"알 수 없는 API 종류: {api_type}")
        client = BaseAPIClient(use_cache=use_cache)
    
    # 유효성 검증 (Ollama와 StableDiffusion의 경우 API 키 검증 대신 연결 검증)
    try:
        if isinstance(client, (StableDiffusionClient, OllamaClient)):
            # validate_api_connection 메서드 사용
            is_valid = await client.validate_api_connection()
            if not is_valid:
                logger.warning(f"API 연결 유효성 검증 실패: {api_type}")
        else:
            # validate_api_key 메서드 사용
            is_valid = await client.validate_api_key()
            if not is_valid:
                logger.warning(f"API 키 유효성 검증 실패: {api_type}")
    except Exception as e:
        logger.error(f"API 유효성 검증 중 오류 발생: {str(e)}")
    
    return client 