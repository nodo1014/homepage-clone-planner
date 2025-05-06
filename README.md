# 홈페이지 클론 기획서 생성기

웹사이트 URL을 분석하여 클론 개발을 위한 구조화된 기획서, 디자인 분석, 목업 이미지 및 응용 아이디어를 자동으로 생성하는 FastAPI 기반 애플리케이션입니다.

## 주요 기능

- URL 기반 웹사이트 자동 분석
- 마크다운 형식의 체계적인 기획서 생성
- 색상 팔레트 및 레이아웃 디자인 요소 추출
- AI 기반 목업 이미지 생성
- 응용 비즈니스 아이디어 제안

## 기술 스택

- **백엔드**: FastAPI, APScheduler, SQLAlchemy
- **프론트엔드**: HTMX, Alpine.js, PicoCSS
- **AI 통합**: OpenAI API, Stable Diffusion, Ollama

## 설치 및 실행

### 요구사항

- Python 3.8 이상
- pip

### 설치 방법

```bash
# 저장소 클론
git clone https://github.com/yourusername/cloner.git
cd cloner

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows에서는 venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정 (.env 파일 생성)
cp .env.example .env
# .env 파일을 편집하여 API 키 등을 설정하세요
```

### 실행 방법

```bash
# 서버 실행
python -m uvicorn main:app --reload
```

이후 웹 브라우저에서 http://localhost:8000 으로 접속하세요.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 제공됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 기여 방법

기여는 언제나 환영합니다! 자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md) 파일을 참조하세요. 