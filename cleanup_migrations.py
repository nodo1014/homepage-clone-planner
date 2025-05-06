#!/usr/bin/env python
"""
마이그레이션 정리 스크립트

이 스크립트는 src/database/migrations/history/ 디렉토리에 있는 
불필요한 마이그레이션 파일들을 안전하게 제거합니다.
migrations.json 파일은 보존됩니다.
"""
import os
import sys
import glob
import json
import shutil
from pathlib import Path
from datetime import datetime

def main():
    # 프로젝트 루트 디렉토리 찾기
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir
    
    # 마이그레이션 디렉토리 경로
    migrations_dir = project_root / "src" / "database" / "migrations"
    migrations_history_dir = migrations_dir / "history"
    migrations_json_file = migrations_dir / "migrations.json"
    
    # 디렉토리 존재 확인
    if not migrations_dir.exists():
        print(f"오류: 마이그레이션 디렉토리를 찾을 수 없습니다: {migrations_dir}")
        return 1
    
    if not migrations_history_dir.exists():
        print(f"오류: 마이그레이션 히스토리 디렉토리를 찾을 수 없습니다: {migrations_history_dir}")
        return 1
    
    # 마이그레이션 파일 개수 확인
    migration_files = list(migrations_history_dir.glob("*.json"))
    files_count = len(migration_files)
    
    if files_count == 0:
        print("마이그레이션 파일이 없습니다. 정리할 필요가 없습니다.")
        return 0
    
    # 현재 migrations.json 파일 백업
    if migrations_json_file.exists():
        backup_file = migrations_dir / f"migrations_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2(migrations_json_file, backup_file)
        print(f"migrations.json 파일 백업 완료: {backup_file}")
    
    # 마이그레이션 파일 정리 확인
    print(f"마이그레이션 파일 {files_count}개를 정리하시겠습니까?")
    print("이 작업은 되돌릴 수 없으며, 필요한 경우 백업을 위해 별도 디렉토리로 이동합니다.")
    confirmation = input("계속하려면 'yes'를 입력하세요: ")
    
    if confirmation.lower() != 'yes':
        print("작업이 취소되었습니다.")
        return 0
    
    # 백업 디렉토리 생성
    backup_dir = migrations_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(exist_ok=True)
    
    # 파일 이동
    for migration_file in migration_files:
        shutil.move(str(migration_file), str(backup_dir / migration_file.name))
    
    print(f"모든 마이그레이션 파일이 백업 디렉토리로 이동되었습니다: {backup_dir}")
    
    # migrations.json 파일 정리 (선택 사항)
    if migrations_json_file.exists():
        try:
            with open(migrations_json_file, 'r', encoding='utf-8') as f:
                migrations_data = json.load(f)
            
            # 적용된 마이그레이션 목록 비우기
            if "applied_migrations" in migrations_data:
                migrations_data["applied_migrations"] = []
            
            # 버전 업데이트
            if "version" in migrations_data:
                migrations_data["version"] = 1
            
            # 마지막 업데이트 시간 설정
            migrations_data["last_updated"] = datetime.now().isoformat()
            
            # 파일 저장
            with open(migrations_json_file, 'w', encoding='utf-8') as f:
                json.dump(migrations_data, f, ensure_ascii=False, indent=2)
            
            print("migrations.json 파일이 정리되었습니다.")
            
        except Exception as e:
            print(f"migrations.json 파일 처리 중 오류가 발생했습니다: {str(e)}")
    
    print("마이그레이션 정리가 완료되었습니다.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 