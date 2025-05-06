#!/bin/bash

# API 키 로드 오류 해결을 위한 스크립트
# "No recommended backend was available" 오류 해결

echo "=== API 키 관리 패키지 설치 ==="
echo "keyrings.alt 패키지를 설치합니다..."

# 가상환경 활성화 확인
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "가상환경이 활성화되어 있지 않습니다!"
    echo "먼저 가상환경을 활성화해주세요:"
    echo "  source venv/bin/activate (Linux/Mac)"
    echo "  venv\\Scripts\\activate (Windows)"
    exit 1
fi

# keyrings.alt 패키지 설치
pip install keyrings.alt

# 설치 결과 확인
if [ $? -eq 0 ]; then
    echo "설치 완료! 이제 API 키 로드 오류가 해결되어야 합니다."
    echo "애플리케이션을 다시 시작해보세요."
else
    echo "설치 중 오류가 발생했습니다."
    echo "수동으로 다음 명령을 실행해보세요: pip install keyrings.alt"
fi

echo ""
echo "참고: 이 문제는 '사용법.md' 문서의 'API 키 저장 관련 문제' 섹션에서도 언급되어 있습니다." 