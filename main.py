"""
홈페이지 클론 기획서 생성기 - FastAPI 애플리케이션

이 파일은 모듈화된 애플리케이션의 진입점 래퍼입니다.
실제 구현은 src/ 디렉토리 내에 있습니다.
"""
import uvicorn
import os
from src.main import create_application, app

# 애플리케이션 생성
application = create_application()

# 애플리케이션 직접 실행 시 동작
if __name__ == "__main__":
    # 포트 설정 (환경 변수 또는 기본값)
    port = int(os.environ.get("PORT", 8000))
    
    # 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=port, 
        reload=True
    ) 