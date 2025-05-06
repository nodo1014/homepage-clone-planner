"""
데이터베이스 관리자 모듈

이 모듈은 데이터베이스 연결, 쿼리 수행, 스키마 관리 등의 기능을 제공합니다.
"""
import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# 로거 설정 - DB 전용 로거 사용
logger = logging.getLogger('src.database')

class DBManager:
    """데이터베이스 관리자 클래스"""
    
    def __init__(self, db_path: str):
        """
        데이터베이스 관리자 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = Path(db_path)
        self.conn = None
        
        # 디렉토리가 없으면 생성
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        
        # 로그 메시지 최적화
        logger.info(f"데이터베이스 관리자 초기화: {db_path}")
    
    def connect(self) -> None:
        """데이터베이스 연결"""
        try:
            # SQLite 연결
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
            logger.debug("데이터베이스 연결 성공")
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 연결 실패: {str(e)}")
            raise
    
    def disconnect(self) -> None:
        """데이터베이스 연결 해제"""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                logger.debug("데이터베이스 연결 해제")
            except sqlite3.Error as e:
                logger.error(f"데이터베이스 연결 해제 실패: {str(e)}")
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
        """
        쿼리 실행
        
        Args:
            query: SQL 쿼리
            params: 쿼리 파라미터
            
        Returns:
            List[Dict]: 쿼리 결과
        """
        if not self.conn:
            self.connect()
        
        results = None
        cursor = None
        
        try:
            cursor = self.conn.cursor()
            
            # 디버그 로깅 시 파라미터가 많을 경우 요약
            if params and len(str(params)) > 100:
                # 로그 크기 제한
                params_log = str(params)[:97] + "..."
                logger.debug(f"쿼리 실행: {query} - 파라미터: {params_log}")
            else:
                logger.debug(f"쿼리 실행: {query} - 파라미터: {params}")
            
            # 쿼리 실행
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # SELECT 쿼리인 경우 결과 반환
            if query.strip().upper().startswith("SELECT"):
                results = [dict(row) for row in cursor.fetchall()]
                # 로그 크기 제한을 위해 결과가 많을 경우 요약
                if results and len(str(results)) > 100:
                    results_log = f"{len(results)}개 항목 반환 (결과 요약됨)"
                    logger.debug(f"쿼리 결과: {results_log}")
                else:
                    logger.debug(f"쿼리 결과: {results}")
            else:
                self.conn.commit()
                results = []
                logger.debug(f"쿼리 실행 완료: {cursor.rowcount}개 행 영향 받음")
            
            return results
        except sqlite3.Error as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"쿼리 실행 실패: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def init_db(self) -> None:
        """데이터베이스 초기화"""
        try:
            if not self.conn:
                self.connect()
            
            logger.info("데이터베이스 초기화 시작")
            
            # 태스크 테이블 생성
            self.execute_query("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    message TEXT,
                    error TEXT,
                    result_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 태스크 단계 테이블 생성
            self.execute_query("""
                CREATE TABLE IF NOT EXISTS task_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            
            logger.info("데이터베이스 초기화 완료")
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 초기화 실패: {str(e)}")
            raise
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        태스크 조회
        
        Args:
            task_id: 태스크 ID
            
        Returns:
            Dict: 태스크 정보
        """
        try:
            results = self.execute_query(
                "SELECT * FROM tasks WHERE id = ?", 
                (task_id,)
            )
            
            return results[0] if results else None
            
        except sqlite3.Error as e:
            logger.error(f"태스크 조회 실패: {str(e)}")
            return None
    
    def create_task(self, task_id: str, url: str) -> bool:
        """
        태스크 생성
        
        Args:
            task_id: 태스크 ID
            url: 분석할 URL
            
        Returns:
            bool: 생성 성공 여부
        """
        from datetime import datetime
        now = datetime.now().isoformat()
        
        try:
            self.execute_query(
                """
                INSERT INTO tasks (id, url, status, progress, message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, url, "pending", 0, "분석 준비 중...", now, now)
            )
            logger.info(f"태스크 생성: {task_id} - {url}")
            return True
        except sqlite3.Error as e:
            logger.error(f"태스크 생성 실패: {str(e)}")
            return False
    
    def update_task(self, task_id: str, status: str, progress: int, message: str = None, 
                   error: str = None, result_id: str = None) -> bool:
        """
        태스크 업데이트
        
        Args:
            task_id: 태스크 ID
            status: 태스크 상태
            progress: 진행률
            message: 상태 메시지
            error: 오류 메시지
            result_id: 결과 ID
            
        Returns:
            bool: 업데이트 성공 여부
        """
        from datetime import datetime
        now = datetime.now().isoformat()
        
        try:
            # 업데이트할 필드 준비
            fields = ["status = ?", "progress = ?", "updated_at = ?"]
            params = [status, progress, now]
            
            if message is not None:
                fields.append("message = ?")
                params.append(message)
            
            if error is not None:
                fields.append("error = ?")
                params.append(error)
            
            if result_id is not None:
                fields.append("result_id = ?")
                params.append(result_id)
            
            # 쿼리 구성
            query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
            params.append(task_id)
            
            # 쿼리 실행
            self.execute_query(query, tuple(params))
            
            # 필요한 정보만 로깅
            log_msg = f"태스크 업데이트: {task_id} - 상태: {status}, 진행률: {progress}%"
            if message:
                log_msg += f", 메시지: {message}"
            if error:
                log_msg += f", 오류: {error}"
            
            logger.info(log_msg)
            return True
        except sqlite3.Error as e:
            logger.error(f"태스크 업데이트 실패: {str(e)}")
            return False
    
    def update_task_step(self, task_id: str, step_index: int, status: str, message: str = None) -> bool:
        """
        태스크 단계 업데이트
        
        Args:
            task_id: 태스크 ID
            step_index: 단계 인덱스
            status: 단계 상태
            message: 상태 메시지
            
        Returns:
            bool: 업데이트 성공 여부
        """
        from datetime import datetime
        now = datetime.now().isoformat()
        
        try:
            # 해당 단계가 존재하는지 확인
            step = self.execute_query(
                "SELECT * FROM task_steps WHERE task_id = ? AND step_index = ?",
                (task_id, step_index)
            )
            
            if step:
                # 기존 단계 업데이트
                query = """
                    UPDATE task_steps 
                    SET status = ?, message = ?, updated_at = ?
                    WHERE task_id = ? AND step_index = ?
                """
                params = (status, message, now, task_id, step_index)
            else:
                # 새 단계 생성
                query = """
                    INSERT INTO task_steps 
                    (task_id, step_index, status, message, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (task_id, step_index, status, message, now, now)
            
            self.execute_query(query, params)
            logger.debug(f"태스크 단계 업데이트: {task_id} - 단계: {step_index}, 상태: {status}")
            return True
        except sqlite3.Error as e:
            logger.error(f"태스크 단계 업데이트 실패: {str(e)}")
            return False
    
    def get_task_with_steps(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        단계 정보를 포함한 태스크 조회
        
        Args:
            task_id: 태스크 ID
            
        Returns:
            Dict: 태스크 정보
        """
        try:
            # 태스크 정보 조회
            task = self.get_task(task_id)
            
            if not task:
                return None
            
            # 태스크 단계 조회
            steps = self.execute_query(
                "SELECT * FROM task_steps WHERE task_id = ? ORDER BY step_index",
                (task_id,)
            )
            
            # 단계 정보 추가
            task["steps"] = steps or []
            
            return task
            
        except sqlite3.Error as e:
            logger.error(f"태스크 및 단계 조회 실패: {str(e)}")
            return None
    
    def delete_task(self, task_id: str) -> bool:
        """
        태스크 삭제
        
        Args:
            task_id: 태스크 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 태스크 삭제 시 외래 키 제약 조건에 의해 관련 단계도 함께 삭제됨
            self.execute_query("DELETE FROM tasks WHERE id = ?", (task_id,))
            logger.info(f"태스크 삭제: {task_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"태스크 삭제 실패: {str(e)}")
            return False
    
    def clean_old_tasks(self, days: int = 7) -> int:
        """
        오래된 태스크 정리
        
        Args:
            days: 보관 기간 (일)
            
        Returns:
            int: 삭제된 태스크 수
        """
        try:
            # n일 이전 생성된 태스크 삭제
            query = """
                DELETE FROM tasks 
                WHERE created_at < datetime('now', ?)
            """
            params = (f"-{days} days",)
            
            # 쿼리 실행
            results = self.execute_query(query, params)
            
            # 삭제된 행 수 확인
            count = self.conn.total_changes
            
            logger.info(f"{days}일 이전 태스크 {count}개 삭제 완료")
            return count
        except sqlite3.Error as e:
            logger.error(f"오래된 태스크 정리 실패: {str(e)}")
            return 0 