#!/usr/bin/env python3
"""
가상 환경 상태 확인 스크립트

이 스크립트는 현재 가상 환경 상태를 확인하고, 필요한 패키지가 설치되어 있는지 확인합니다.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def is_venv():
    """현재 가상 환경인지 확인"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def check_python_version():
    """파이썬 버전 확인"""
    major, minor, micro = sys.version_info[:3]
    print(f"파이썬 버전: {major}.{minor}.{micro}")
    
    if major < 3 or (major == 3 and minor < 8):
        print("❌ 파이썬 3.8 이상이 필요합니다.")
        return False
    else:
        print("✅ 파이썬 버전 요구사항 충족 (3.8 이상)")
        return True

def check_packages():
    """주요 패키지 설치 여부 확인"""
    required_packages = [
        "fastapi", "uvicorn", "jinja2", "sqlalchemy", 
        "beautifulsoup4", "httpx", "markdown",
        "python-dotenv", "apscheduler", "aiohttp"
    ]
    
    installed_packages = []
    try:
        import pkg_resources
        installed_packages = {pkg.key for pkg in pkg_resources.working_set}
    except ImportError:
        print("❌ pkg_resources 모듈을 불러올 수 없습니다.")
        return False
    
    all_installed = True
    print("\n필수 패키지 확인:")
    
    for package in required_packages:
        if package.lower() in installed_packages:
            print(f"✅ {package}")
        else:
            print(f"❌ {package} - 설치 필요")
            all_installed = False
    
    return all_installed

def check_env_file():
    """환경 변수 파일 확인"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("\n✅ .env 파일이 존재합니다.")
        return True
    elif env_example.exists():
        print("\n❌ .env 파일이 없습니다. .env.example 파일을 복사하세요.")
        print("   명령어: cp .env.example .env")
        return False
    else:
        print("\n❌ .env 파일과 .env.example 파일이 모두 없습니다.")
        return False

def check_directories():
    """필요한 디렉토리 확인"""
    required_dirs = ["logs", "database", "outputs", "exports"]
    
    print("\n디렉토리 확인:")
    all_dirs_exist = True
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            print(f"✅ {dir_name}/")
        else:
            print(f"❌ {dir_name}/ - 생성 필요")
            all_dirs_exist = False
    
    return all_dirs_exist

def create_missing_directories():
    """누락된 디렉토리 생성"""
    required_dirs = ["logs", "database", "outputs", "exports"]
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"✅ {dir_name}/ 디렉토리를 생성했습니다.")

def main():
    """메인 함수"""
    print("=" * 50)
    print("     홈페이지 클론 기획서 생성기 환경 확인     ")
    print("=" * 50)
    
    # 가상 환경 확인
    if is_venv():
        print("✅ 가상 환경이 활성화되어 있습니다.")
    else:
        print("❌ 가상 환경이 활성화되어 있지 않습니다!")
        print("   명령어: source venv/bin/activate (Linux/Mac)")
        print("   명령어: venv\\Scripts\\activate (Windows)")
        return
    
    # 파이썬 버전 확인
    python_ok = check_python_version()
    
    # 패키지 확인
    packages_ok = check_packages()
    
    # 환경 변수 파일 확인
    env_ok = check_env_file()
    
    # 디렉토리 확인
    dirs_ok = check_directories()
    
    if not dirs_ok:
        user_input = input("\n누락된 디렉토리를 생성하시겠습니까? (y/n): ")
        if user_input.lower() == 'y':
            create_missing_directories()
    
    # 종합 결과
    print("\n" + "=" * 50)
    print("               종합 결과                ")
    print("=" * 50)
    
    all_ok = python_ok and packages_ok and env_ok and dirs_ok
    
    if all_ok:
        print("✅ 모든 요구사항이 충족되었습니다!")
        print("   명령어로 서버를 시작하세요: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("❌ 일부 요구사항이 충족되지 않았습니다. 위 메시지를 확인하세요.")
        
        if not packages_ok:
            print("\n누락된 패키지를 설치하려면:")
            print("   명령어: pip install -r requirements.txt")

if __name__ == "__main__":
    main() 