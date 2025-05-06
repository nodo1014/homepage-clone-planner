.PHONY: setup venv run test clean check-env

# 프로젝트 기본 변수
VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip
MAIN = main.py
PORT = 9000

# 기본 target
all: setup

# 가상환경 상태 확인
check-env:
	@if [ -n "$$VIRTUAL_ENV" ]; then \
		echo "이미 가상환경에 있습니다: $$VIRTUAL_ENV"; \
	else \
		echo "가상환경에 있지 않습니다."; \
	fi

# 가상환경 설정
venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "가상환경 생성 중..."; \
		python -m venv $(VENV_DIR); \
	else \
		echo "가상환경이 이미 존재합니다."; \
	fi

# 의존성 설치
setup: venv
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "가상환경 활성화가 필요합니다."; \
		echo "먼저 'source $(VENV_DIR)/bin/activate' 명령을 실행하세요."; \
	else \
		echo "의존성 설치 중..."; \
		$(PIP) install -r requirements.txt; \
	fi

# 서버 실행
run:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "가상환경 활성화가 필요합니다."; \
		echo "먼저 'source $(VENV_DIR)/bin/activate' 명령을 실행하세요."; \
	else \
		echo "서버 실행 중..."; \
		$(PYTHON) $(MAIN); \
	fi

# 테스트 실행
test:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "가상환경 활성화가 필요합니다."; \
		echo "먼저 'source $(VENV_DIR)/bin/activate' 명령을 실행하세요."; \
	else \
		echo "테스트 실행 중..."; \
		$(PYTHON) -m pytest src/tests/test_integration.py -v; \
	fi

# 가상환경 상태 확인
status:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "가상환경 활성화가 필요합니다."; \
		echo "먼저 'source $(VENV_DIR)/bin/activate' 명령을 실행하세요."; \
	else \
		$(PYTHON) venv_status.py; \
	fi

# 정리
clean:
	@echo "생성된 캐시 파일 삭제 중..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".coverage" -exec rm -rf {} +
	@echo "정리 완료" 