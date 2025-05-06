#!/bin/bash
# 홈페이지 클론 기획서 생성기 시작 스크립트

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== 홈페이지 클론 기획서 생성기 시작 스크립트 =====${NC}"

# 현재 디렉토리 확인
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo -e "${BLUE}프로젝트 디렉토리:${NC} $PROJECT_DIR"

# 가상환경 확인
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}가상환경이 없습니다. 생성 중...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}가상환경 생성 실패! 파이썬 3가 설치되어 있는지 확인하세요.${NC}"
        exit 1
    fi
    echo -e "${GREEN}가상환경 생성 완료!${NC}"
fi

# 가상환경 활성화
echo -e "${BLUE}가상환경 활성화 중...${NC}"
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo -e "${RED}가상환경 활성화 실패!${NC}"
    exit 1
fi
echo -e "${GREEN}가상환경 활성화 완료!${NC}"

# requirements.txt 설치 확인
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${RED}requirements.txt 파일이 없습니다!${NC}"
    exit 1
fi

echo -e "${BLUE}패키지 설치 상태 확인 중...${NC}"
MISSING_PACKAGES=0
for pkg in fastapi uvicorn jinja2 sqlalchemy beautifulsoup4 httpx; do
    if ! pip list | grep -i "$pkg" > /dev/null; then
        MISSING_PACKAGES=1
        break
    fi
done

if [ $MISSING_PACKAGES -eq 1 ]; then
    echo -e "${YELLOW}일부 패키지가 누락되었습니다. requirements.txt 설치 중...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}패키지 설치 실패!${NC}"
        exit 1
    fi
    echo -e "${GREEN}패키지 설치 완료!${NC}"
else
    echo -e "${GREEN}필수 패키지가 이미 설치되어 있습니다.${NC}"
fi

# keyring.alt 패키지 설치 (API 키 저장 문제 해결)
if ! pip list | grep -i "keyrings.alt" > /dev/null; then
    echo -e "${YELLOW}keyrings.alt 패키지가 없습니다. 설치 중...${NC}"
    pip install keyrings.alt
    if [ $? -ne 0 ]; then
        echo -e "${RED}keyrings.alt 패키지 설치 실패! API 키 저장에 문제가 발생할 수 있습니다.${NC}"
    else
        echo -e "${GREEN}keyrings.alt 패키지 설치 완료!${NC}"
    fi
fi

# 필요한 디렉토리 생성
for dir in logs database outputs exports; do
    if [ ! -d "$PROJECT_DIR/$dir" ]; then
        echo -e "${YELLOW}$dir 디렉토리가 없습니다. 생성 중...${NC}"
        mkdir -p "$PROJECT_DIR/$dir"
        echo -e "${GREEN}$dir 디렉토리 생성 완료!${NC}"
    fi
done

# .env 파일 확인
if [ ! -f "$PROJECT_DIR/.env" ]; then
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        echo -e "${YELLOW}.env 파일이 없습니다. .env.example에서 복사 중...${NC}"
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo -e "${GREEN}.env 파일 생성 완료!${NC}"
    else
        echo -e "${YELLOW}.env 파일과 .env.example 파일이 모두 없습니다. 기본 .env 파일 생성 중...${NC}"
        cat > "$PROJECT_DIR/.env" << EOF
# 환경 변수 설정
DEBUG=True
API_MODE=free
EOF
        echo -e "${GREEN}기본 .env 파일 생성 완료!${NC}"
    fi
fi

# 모듈화 구조 검사
if [ -f "$PROJECT_DIR/main_new.py" ]; then
    echo -e "${BLUE}모듈화된 구조를 사용합니다.${NC}"
    RUN_FILE="main_new.py"
else
    echo -e "${YELLOW}기존 구조를 사용합니다.${NC}"
    RUN_FILE="main.py"
fi

# 서버 시작
echo -e "${BLUE}서버 시작 중...${NC}"
echo -e "${GREEN}애플리케이션이 http://localhost:8000 에서 실행됩니다.${NC}"
echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요.${NC}"
echo -e "${BLUE}=====================================${NC}"

# 모듈화된 구조 실행
python -m uvicorn $RUN_FILE:app --reload --host 0.0.0.0 --port 8000 