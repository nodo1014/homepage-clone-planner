"""
PDF 내보내기 예제

이 스크립트는 클론 기획서를 PDF 형식으로 내보내는 예제를 보여줍니다.
"""
import os
import sys
from pathlib import Path
import json
import logging

# 상위 디렉토리를 시스템 경로에 추가
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
project_root = src_dir.parent
sys.path.append(str(project_root))

from src.export.export_manager import ExportManager, markdown_to_pdf, html_to_pdf

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """PDF 내보내기 예제 실행"""
    
    # 예제 데이터 생성
    example_content = {
        "title": "홈페이지 클론 기획서 - 예제 웹사이트",
        "description": "이 기획서는 예제 웹사이트의 클론 구현을 위한 지침을 제공합니다.",
        "website": {
            "name": "예제 웹사이트",
            "url": "https://example.com",
            "description": "간단한 포트폴리오 웹사이트"
        },
        "structure": {
            "header": {
                "logo": True,
                "navigation": True,
                "search": False
            },
            "main_sections": [
                "히어로 섹션",
                "서비스 소개",
                "포트폴리오",
                "연락처"
            ],
            "footer": {
                "copyright": True,
                "social_links": True,
                "contact_info": True
            }
        },
        "design_analysis": {
            "colors": [
                {"name": "주요 색상", "hex": "#1a73e8"},
                {"name": "배경 색상", "hex": "#ffffff"},
                {"name": "강조 색상", "hex": "#ff5722"}
            ],
            "fonts": [
                {"name": "Roboto", "usage": "본문"},
                {"name": "Montserrat", "usage": "제목"}
            ],
            "layout": "반응형 그리드 레이아웃"
        },
        "development_recommendations": "모바일 최적화와 접근성을 고려한 개발이 필요합니다.",
        "conclusion": "이 웹사이트의 클론 개발은 약 2주 정도 소요될 것으로 예상됩니다."
    }
    
    # 1. ExportManager를 사용한 PDF 내보내기
    logger.info("ExportManager를 사용한 PDF 내보내기 시작")
    output_dir = project_root / "outputs" / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    manager = ExportManager(output_dir)
    pdf_path = manager.export_to_pdf(example_content, "example_report")
    logger.info(f"PDF 파일 생성 완료: {pdf_path}")
    
    # 2. 지원되는 모든 형식으로 내보내기 (ZIP 포함)
    logger.info("모든 형식으로 내보내기 시작 (ZIP 포함)")
    zip_path = manager.export_to_zip(example_content, "example_all_formats")
    logger.info(f"ZIP 파일 생성 완료: {zip_path}")
    
    # 3. 마크다운에서 PDF로 직접 변환 예제
    logger.info("마크다운에서 PDF로 직접 변환 예제")
    
    # 먼저 마크다운 파일 생성
    md_path = manager.export_to_markdown(example_content, "example_markdown")
    
    # 마크다운에서 PDF로 변환
    md_to_pdf_path = output_dir / "example_markdown_to_pdf.pdf"
    pdf_from_md = markdown_to_pdf(md_path, md_to_pdf_path)
    logger.info(f"마크다운에서 PDF 변환 완료: {pdf_from_md}")
    
    logger.info("모든 PDF 내보내기 예제 완료")
    logger.info(f"결과 파일이 저장된 디렉토리: {output_dir}")

if __name__ == "__main__":
    main() 