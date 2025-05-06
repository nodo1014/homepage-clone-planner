#!/bin/bash
# 홈페이지 클론 기획서 생성기 - 빠른 시작 스크립트

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== 홈페이지 클론 기획서 생성기 - 빠른 시작 =====${NC}"
echo -e "${YELLOW}이 스크립트는 필수 설정을 자동으로 구성하고 애플리케이션을 시작합니다.${NC}"

# 현재 디렉토리 확인
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo -e "${BLUE}프로젝트 디렉토리:${NC} $PROJECT_DIR"

# 가상환경 생성 및 활성화
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}가상환경 생성 중...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}오류: 가상환경 생성 실패! Python 3가 설치되어 있는지 확인하세요.${NC}"
        exit 1
    fi
    echo -e "${GREEN}가상환경 생성 완료!${NC}"
fi

echo -e "${YELLOW}가상환경 활성화 중...${NC}"
source "venv/bin/activate"
echo -e "${GREEN}가상환경 활성화 완료!${NC}"

# 필수 패키지 설치
echo -e "${YELLOW}필수 패키지 설치 중...${NC}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}오류: 패키지 설치 실패! 인터넷 연결을 확인하세요.${NC}"
    exit 1
fi
echo -e "${GREEN}패키지 설치 완료!${NC}"

# API 키 관리 문제 해결을 위한 패키지 설치
echo -e "${YELLOW}API 키 관리 패키지 설치 중...${NC}"
pip install keyrings.alt
echo -e "${GREEN}API 키 관리 패키지 설치 완료!${NC}"

# 필요한 디렉토리 생성
echo -e "${YELLOW}필요한 디렉토리 생성 중...${NC}"
for dir in logs database outputs exports; do
    mkdir -p $dir
done
echo -e "${GREEN}디렉토리 생성 완료!${NC}"

# 기본 환경 변수 설정
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}기본 환경 변수 설정 중...${NC}"
    cat > ".env" << EOF
# 기본 환경 설정
DEBUG=True
API_MODE=free

# API 키 설정 (필요한 경우 아래 값을 입력하세요)
# OPENAI_API_KEY=your_openai_api_key
# CLAUDE_API_KEY=your_claude_api_key
EOF
    echo -e "${GREEN}기본 환경 변수 설정 완료!${NC}"
fi

# 사용법 안내
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}설정이 완료되었습니다!${NC}"
echo -e "${YELLOW}애플리케이션을 시작하시겠습니까? (y/n)${NC}"
read -r RESPONSE
if [[ "$RESPONSE" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${BLUE}애플리케이션 시작 중...${NC}"
    echo -e "${GREEN}웹 브라우저에서 http://localhost:8000 으로 접속하세요.${NC}"
    echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요.${NC}"
    
    # 파일 존재 여부에 따라 실행할 파일 결정
    if [ -f "main.py" ]; then
        python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    else
        echo -e "${RED}오류: main.py 파일을 찾을 수 없습니다!${NC}"
        exit 1
    fi
else
    echo -e "${BLUE}애플리케이션을 시작하지 않습니다.${NC}"
    echo -e "${YELLOW}나중에 다음 명령으로 시작할 수 있습니다:${NC}"
    echo -e "${GREEN}source venv/bin/activate && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000${NC}"
fi 