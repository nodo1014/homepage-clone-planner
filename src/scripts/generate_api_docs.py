#!/usr/bin/env python3
"""
API 문서 생성 스크립트

이 스크립트는 FastAPI 애플리케이션의 API 문서를 자동으로 생성합니다.
실행 방법: python -m src.scripts.generate_api_docs main:app --output-dir docs
"""
import argparse
import importlib.util
import logging
import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 모듈 검색 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.api_docs_generator import generate_api_docs

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="FastAPI 애플리케이션의 API 문서 생성")
    parser.add_argument("app_path", help="FastAPI 앱 모듈 경로 (예: main:app)")
    parser.add_argument("--output-dir", "-o", default="docs", help="출력 디렉토리 경로")
    parser.add_argument("--title", "-t", default="홈페이지 클론 기획서 생성기 API 문서", help="문서 제목")
    parser.add_argument("--description", "-d", 
                        default="이 문서는 홈페이지 클론 기획서 생성기의 API 엔드포인트를 설명합니다.", 
                        help="문서 설명")
    parser.add_argument("--formats", "-f", default="md,html", help="생성할 문서 형식 (쉼표로 구분)")
    parser.add_argument("--include-code", "-c", action="store_true", help="핸들러 함수 소스코드 포함")
    parser.add_argument("--css", help="HTML 문서용 CSS 스타일시트 경로")
    
    args = parser.parse_args()
    
    # FastAPI 앱 모듈 로드
    try:
        module_path, app_var = args.app_path.split(":")
        
        if module_path.endswith(".py"):
            module_path = module_path[:-3]
            
        logger.info(f"모듈 로드 중: {module_path}")
        try:
            # 먼저 일반적인 방법으로 모듈 임포트 시도
            module = importlib.import_module(module_path)
        except ImportError:
            # 실패하면 파일 경로로 로드 시도
            logger.info(f"파일 경로로 모듈 로드 시도: {module_path}.py")
            spec = importlib.util.spec_from_file_location(module_path, f"{module_path}.py")
            if not spec or not spec.loader:
                raise ImportError(f"모듈을 찾을 수 없습니다: {module_path}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        
        app = getattr(module, app_var)
        logger.info(f"FastAPI 앱 로드 완료: {app_var}")
        
        # 문서 형식 파싱
        formats = args.formats.split(",")
        
        # 출력 디렉토리 확인
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"출력 디렉토리: {output_dir}")
        
        # API 문서 생성
        result_files = generate_api_docs(
            app=app,
            output_dir=str(output_dir),
            title=args.title,
            description=args.description,
            formats=formats,
            include_code=args.include_code,
            css=args.css
        )
        
        logger.info("API 문서 생성 완료:")
        for fmt, path in result_files.items():
            logger.info(f"- {fmt.upper()}: {path}")
            
        # 결과 요약
        print("\n===== API 문서 생성 완료 =====")
        print(f"제목: {args.title}")
        for fmt, path in result_files.items():
            print(f"- {fmt.upper()}: {path}")
        print("===========================")
        
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 