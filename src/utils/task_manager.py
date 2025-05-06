"""
작업 상태 관리 모듈

이 모듈은 웹사이트 분석 작업의 상태와 진행률을 관리합니다.
메모리 내 저장소를 사용하여 작업 상태를 추적합니다.
"""
import uuid
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

# 작업 상태 저장소
tasks: Dict[str, Dict[str, Any]] = {}

# 작업 만료 시간 (2시간)
TASK_EXPIRY_SECONDS = 7200

# 출력 디렉토리
output_dir: Path = None

def init_manager(output_directory: str = None) -> None:
    """
    작업 관리자를 초기화합니다.
    
    Args:
        output_directory: 결과를 저장할 디렉토리 경로
    """
    global output_dir
    
    if output_directory:
        output_dir = Path(output_directory)
        os.makedirs(output_dir, exist_ok=True)
    else:
        # 기본 출력 디렉토리 설정
        output_dir = Path(os.getcwd()) / "outputs"
        os.makedirs(output_dir, exist_ok=True)

def create_task(url: str) -> str:
    """
    새로운 작업을 생성하고 작업 ID를 반환합니다.
    
    Args:
        url: 분석할 웹사이트 URL
        
    Returns:
        str: 생성된 작업 ID
    """
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "id": task_id,
        "url": url,
        "status": "pending",
        "progress": 0,
        "message": "분석 요청 처리 중...",
        "result_id": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "steps": [
            {"name": "페이지 구조 분석", "status": "pending", "message": ""},
            {"name": "콘텐츠 추출 및 분류", "status": "pending", "message": ""},
            {"name": "메뉴 및 내비게이션 분석", "status": "pending", "message": ""},
            {"name": "디자인 요소 추출", "status": "pending", "message": ""},
            {"name": "기획서 생성", "status": "pending", "message": ""},
            {"name": "목업 이미지 생성", "status": "pending", "message": ""},
            {"name": "아이디어 제안 생성", "status": "pending", "message": ""}
        ],
        "logs": [],
        "errors": []
    }
    
    # 오래된 작업 정리
    cleanup_expired_tasks()
    
    return task_id

def update_task_status(
    task_id: str, 
    status: str = None, 
    progress: int = None,
    message: str = None,
    result_id: str = None,
    error: str = None
) -> Dict[str, Any]:
    """
    작업 상태를 업데이트합니다.
    
    Args:
        task_id: 작업 ID
        status: 작업 상태 (pending, running, completed, error)
        progress: 진행률 (0-100)
        message: 상태 메시지
        result_id: 결과 ID (완료 시)
        error: 오류 메시지 (오류 발생 시)
        
    Returns:
        Dict: 업데이트된 작업 상태
    """
    if task_id not in tasks:
        return None
    
    task = tasks[task_id]
    task["updated_at"] = datetime.now()
    
    if status:
        task["status"] = status
    
    if progress is not None:
        task["progress"] = progress
    
    if message:
        task["message"] = message
        task["logs"].append({
            "timestamp": datetime.now().isoformat(),
            "message": message
        })
    
    if result_id:
        task["result_id"] = result_id
    
    if error:
        task["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "message": error
        })
    
    return task

def update_step_status(
    task_id: str,
    step_index: int,
    status: str,
    message: str = None
) -> Dict[str, Any]:
    """
    특정 작업 단계의 상태를 업데이트합니다.
    
    Args:
        task_id: 작업 ID
        step_index: 단계 인덱스 (0부터 시작)
        status: 단계 상태 (pending, running, completed, error)
        message: 상태 메시지
        
    Returns:
        Dict: 업데이트된 작업 상태
    """
    if task_id not in tasks:
        return None
    
    task = tasks[task_id]
    
    if 0 <= step_index < len(task["steps"]):
        step = task["steps"][step_index]
        step["status"] = status
        
        if message:
            step["message"] = message
            
        # 진행률 계산
        completed_steps = sum(1 for step in task["steps"] if step["status"] == "completed")
        in_progress_steps = sum(1 for step in task["steps"] if step["status"] == "running")
        
        total_steps = len(task["steps"])
        progress = int((completed_steps + in_progress_steps * 0.5) / total_steps * 100)
        
        task["progress"] = progress
        
        # 현재 단계 메시지로 업데이트
        if status == "running" and message:
            task["message"] = f"{step['name']} - {message}"
        elif status == "running":
            task["message"] = f"{step['name']} 진행 중..."
        
        # 모든 단계가 완료되었는지 확인
        if all(step["status"] == "completed" for step in task["steps"]):
            task["status"] = "completed"
            task["progress"] = 100
            task["message"] = "분석 완료!"
            
            # 결과 ID가 없으면 생성 (result_{task_id} 형식으로 통일)
            if not task.get("result_id"):
                task["result_id"] = f"result_{task_id}"
                
        # 작업 상태 업데이트
        task["updated_at"] = datetime.now()
    
    return task

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    작업 상태를 가져옵니다.
    
    Args:
        task_id: 작업 ID
        
    Returns:
        Dict: 작업 상태 정보
    """
    if task_id not in tasks:
        return None
    
    return tasks[task_id]

def get_all_tasks() -> Dict[str, Dict[str, Any]]:
    """
    모든 작업 정보를 가져옵니다.
    
    Returns:
        Dict: 작업 ID를 키로 하는 모든 작업 정보
    """
    return tasks

def delete_task(task_id: str) -> bool:
    """
    작업을 삭제합니다.
    
    Args:
        task_id: 삭제할 작업 ID
        
    Returns:
        bool: 삭제 성공 여부
    """
    if task_id not in tasks:
        return False
    
    del tasks[task_id]
    return True

def cleanup_expired_tasks() -> None:
    """
    만료된 작업을 정리합니다.
    """
    expiry_time = datetime.now() - timedelta(seconds=TASK_EXPIRY_SECONDS)
    
    expired_task_ids = [
        task_id for task_id, task in tasks.items()
        if task["updated_at"] < expiry_time
    ]
    
    for task_id in expired_task_ids:
        del tasks[task_id]

def get_active_tasks() -> List[Dict[str, Any]]:
    """
    현재 활성화된 모든 작업 목록을 가져옵니다.
    
    Returns:
        List: 활성화된 작업 목록
    """
    return [task for task_id, task in tasks.items() 
            if task["status"] in ["pending", "running"]]

# 테스트용 기능: 임의의 진행 상태 시뮬레이션
def simulate_progress(task_id: str) -> None:
    """
    테스트용: 작업 진행 상태를 시뮬레이션합니다.
    실제 구현에서는 실제 분석 로직과 연결됩니다.
    
    Args:
        task_id: 작업 ID
    """
    task = get_task_status(task_id)
    if not task or task["status"] == "completed" or task["status"] == "error":
        return
    
    # 작업 상태를 running으로 변경
    update_task_status(task_id, status="running", message="분석 시작 중...")
    
    # 각 단계별 진행
    for i, step in enumerate(task["steps"]):
        if step["status"] != "completed":
            update_step_status(task_id, i, "running")
            time.sleep(2)  # 실제 구현에서는, 실제 작업 시간에 따라 달라짐
            update_step_status(task_id, i, "completed")
    
    # 작업 완료
    update_task_status(
        task_id, 
        status="completed", 
        progress=100, 
        message="분석 완료!", 
        result_id=f"result_{task_id}"
    ) 