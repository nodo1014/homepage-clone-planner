#!/bin/bash

# 가상환경 한 번만 진입하는 스크립트
# 사용법: source activate_once.sh

# 가상환경 경로 설정 (필요에 따라 수정)
VENV_PATH="./venv"

# 이미 가상환경에 있는지 확인
if [ -z "$VIRTUAL_ENV" ]; then
    echo "가상환경 활성화 중..."
    if [ -f "$VENV_PATH/bin/activate" ]; then
        source "$VENV_PATH/bin/activate"
        echo "가상환경이 활성화되었습니다."
    else
        echo "오류: 가상환경을 찾을 수 없습니다. ($VENV_PATH)"
        echo "먼저 'python -m venv venv' 명령으로 가상환경을 생성하세요."
    fi
else
    echo "이미 가상환경에 있습니다: $VIRTUAL_ENV"
    # 현재 중첩된 가상환경인지 확인 (환경변수에 여러 경로가 포함된 경우)
    if [[ "$VIRTUAL_ENV" == *";"* ]] || [[ "$VIRTUAL_ENV" == *":"* ]]; then
        echo "경고: 중첩된 가상환경이 감지되었습니다."
    fi
fi 