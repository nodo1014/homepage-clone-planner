import time
import logging

def clean_database(outputs_dir):
    """오래된 임시 파일 정리 작업"""
    try:
        temp_dirs = [outputs_dir / "temp"]
        now = time.time()
        for temp_dir in temp_dirs:
            if not temp_dir.exists():
                continue
            for file_path in temp_dir.glob("**/*"):
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    age_days = (now - mtime) / (60 * 60 * 24)
                    if age_days > 7:
                        file_path.unlink()
        logging.getLogger(__name__).info("데이터베이스 및 임시 파일 정리 완료")
    except Exception as e:
        logging.getLogger(__name__).error(f"데이터베이스 정리 중 오류 발생: {str(e)}") 