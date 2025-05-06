"""
통합 테스트 모듈

이 모듈은 홈페이지 클론 기획서 생성기의 전체 워크플로우를 테스트합니다.
주요 기능, API 엔드포인트 및 사용자 시나리오를 검증합니다.
"""
import sys
import os
import pytest
import json
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# 프로젝트 루트 디렉토리를 임포트 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 테스트할 애플리케이션 임포트
from main import app
from src.utils.task_manager import create_task, get_task_status, update_task_status
from src.analyzer.fetcher import fetch_website_content
from src.analyzer.analyzer import analyze_website
from src.export.export_manager import ExportManager

# 테스트 클라이언트 생성
client = TestClient(app)

# 테스트 데이터 디렉토리
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_OUTPUT_DIR = Path(__file__).parent / "test_output"

# 테스트 URL
TEST_URLS = [
    "https://www.example.com",
    "https://fastapi.tiangolo.com",
    "https://htmx.org",
]

# 테스트 전후 설정
@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    """테스트 전 설정 및 이후 정리 작업"""
    # 테스트 디렉토리 생성
    TEST_DATA_DIR.mkdir(exist_ok=True)
    TEST_OUTPUT_DIR.mkdir(exist_ok=True)
    
    # 테스트 실행
    yield
    
    # 테스트 정리 (주석 처리: 디버깅을 위해 출력 파일 유지)
    # if TEST_OUTPUT_DIR.exists():
    #     shutil.rmtree(TEST_OUTPUT_DIR)

@pytest.mark.skip(reason="실제 API 호출이 발생하므로 필요시 수동으로 실행")
def test_full_workflow():
    """전체 워크플로우 테스트"""
    test_url = TEST_URLS[0]
    
    # 1. URL 분석 요청
    response = client.post("/analyze", data={"url": test_url})
    assert response.status_code == 200
    
    # 작업 ID 추출
    task_id = None
    for line in response.content.decode().split("\n"):
        if "task_id" in line:
            # JavaScript 할당 구문에서 task_id 추출
            task_id = line.split('=')[1].strip().strip('"').strip("'").strip(';')
            break
    
    assert task_id is not None, "작업 ID를 찾을 수 없습니다."
    
    # 2. 작업 상태 확인 (최대 30초 대기)
    import time
    max_tries = 30
    tries = 0
    complete = False
    
    while tries < max_tries and not complete:
        response = client.get(f"/analyze/status/{task_id}")
        assert response.status_code == 200
        data = response.json()
        
        print(f"작업 상태: {data['status']}, 진행률: {data['progress']}%")
        
        if data["status"] == "completed":
            complete = True
            result_id = data["result_id"]
            assert result_id is not None
            break
        
        if data["status"] == "error":
            pytest.fail(f"분석 중 오류 발생: {data.get('message', '알 수 없는 오류')}")
        
        tries += 1
        time.sleep(1)
    
    assert complete, f"최대 시도 횟수({max_tries})에 도달했지만 작업이 완료되지 않았습니다."
    
    # 3. 결과 보기
    response = client.get(f"/results/{result_id}")
    assert response.status_code == 200
    
    # 4. 다양한 형식으로 내보내기 테스트
    # 마크다운 내보내기
    response = client.get(f"/export/{result_id}/markdown")
    assert response.status_code in (200, 303)  # 200 OK 또는 303 See Other (리다이렉트)
    
    # PDF 내보내기
    response = client.get(f"/export/{result_id}/pdf")
    assert response.status_code in (200, 303)
    
    # ZIP 내보내기
    response = client.get(f"/export/{result_id}/zip")
    assert response.status_code in (200, 303)
    
    # JSON 내보내기
    response = client.get(f"/export/{result_id}/json")
    assert response.status_code in (200, 303)

# 노션 내보내기 테스트 (모킹)
@patch("src.export.export_manager.NotionClient")
def test_notion_export_with_mock(mock_notion_client):
    """노션 내보내기 기능 테스트 (실제 API 호출 없음)"""
    # 노션 클라이언트 모킹
    mock_instance = MagicMock()
    mock_instance.export_website_analysis.return_value = "mock-page-id-12345"
    mock_notion_client.return_value = mock_instance
    
    # 테스트 파일 확인
    result_path = Path("results/result_test.json")
    if not result_path.exists():
        pytest.skip("테스트 결과 파일이 없습니다: results/result_test.json")
    
    # ExportManager 직접 호출하여 테스트
    with patch.dict(os.environ, {"NOTION_PARENT_PAGE_ID": "test-parent-id", "NOTION_API_KEY": "test-api-key"}):
        from src.export.export_manager import ExportManager
        export_manager = ExportManager()
        
        # 결과 콘텐츠 로드
        with open(result_path, "r", encoding="utf-8") as f:
            result_content = json.load(f)
        
        # 직접 함수 호출하여 테스트
        page_url = export_manager.export_to_notion(
            content=result_content,
            parent_id="test-parent-id",
            api_key="test-api-key"
        )
        
        # 호출되었는지 확인
        mock_instance.export_website_analysis.assert_called_once()
        
        # URL 형식 확인
        assert "mock-page-id" in page_url
        assert page_url.startswith("https://www.notion.so/")

# 구글 드라이브 내보내기 테스트 (모킹)
@patch("src.export.export_manager.GoogleDriveClient")
def test_google_drive_export_with_mock(mock_gdrive_client):
    """구글 드라이브 내보내기 기능 테스트 (실제 API 호출 없음)"""
    # 구글 드라이브 클라이언트 모킹
    mock_instance = MagicMock()
    mock_instance.export_to_google_drive.return_value = (True, "mock-file-id", "https://drive.google.com/file/d/mock-file-id/view")
    mock_gdrive_client.return_value = mock_instance
    
    # 파일 존재 체크 모킹
    with patch("os.path.exists", return_value=True):
        # 환경 변수 모킹
        with patch.dict(os.environ, {"GOOGLE_CREDENTIALS_FILE": "test-creds.json"}):
            # 구글 드라이브 내보내기 요청
            response = client.get("/export/result_test/gdrive")
            assert response.status_code == 200
            
            # 응답 내용 확인
            data = response.json()
            assert data["status"] == "success"
            assert "drive.google.com" in data["url"]

# 이메일 전송 테스트 (모킹)
@patch("src.export.email_sender.EmailSender")
def test_email_sending_with_mock(mock_email_sender):
    """이메일 전송 기능 테스트 (실제 이메일 전송 없음)"""
    # 이메일 전송 성공 모킹
    mock_instance = MagicMock()
    mock_instance.send_results_email.return_value = True
    mock_email_sender.return_value = mock_instance
    
    # 이메일 전송 요청
    response = client.post("/send-email/result_test", data={"email": "test@example.com"})
    assert response.status_code == 200
    
    # 응답 내용 확인
    data = response.json()
    assert data["status"] == "success"

# 내보내기 관리자 단위 테스트
def test_export_manager():
    """내보내기 관리자 기능 테스트"""
    # 테스트용 콘텐츠
    test_content = {
        "title": "테스트 웹사이트 기획서",
        "website": {
            "name": "테스트 웹사이트",
            "url": "https://www.example.com",
            "description": "테스트 설명"
        },
        "design_analysis": {
            "colors": ["#FF0000", "#00FF00", "#0000FF"],
            "layout": "반응형 그리드 레이아웃"
        }
    }
    
    # 내보내기 관리자 생성
    export_manager = ExportManager(TEST_OUTPUT_DIR)
    
    # 마크다운 내보내기 테스트
    md_path = export_manager.export_to_markdown(test_content, "test_export")
    assert Path(md_path).exists()
    
    # JSON 내보내기 테스트
    json_path = export_manager.export_to_json(test_content, "test_export")
    assert Path(json_path).exists()
    
    # 내보낸 JSON 파일이 올바른 내용을 포함하는지 확인
    with open(json_path, "r", encoding="utf-8") as f:
        json_content = json.load(f)
    
    assert json_content["title"] == test_content["title"]
    assert json_content["website"]["url"] == test_content["website"]["url"]

# 작업 관리자 테스트
def test_task_manager():
    """작업 관리자 기능 테스트"""
    # 작업 생성
    task_id = create_task("https://www.example.com")
    assert task_id is not None
    
    # 작업 상태 확인
    task = get_task_status(task_id)
    assert task is not None
    assert task["status"] == "pending"
    assert task["url"] == "https://www.example.com"
    
    # 작업 상태 업데이트
    update_task_status(task_id, status="running", progress=50, message="테스트 중...")
    task = get_task_status(task_id)
    assert task["status"] == "running"
    assert task["progress"] == 50
    assert task["message"] == "테스트 중..."
    
    # 작업 완료
    update_task_status(task_id, status="completed", progress=100, message="완료", result_id=f"result_{task_id}")
    task = get_task_status(task_id)
    assert task["status"] == "completed"
    assert task["progress"] == 100
    assert task["result_id"] == f"result_{task_id}"

# 웹 페이지 가져오기 테스트
@pytest.mark.asyncio
@pytest.mark.skip(reason="실제 웹사이트에 접근하므로 필요시 수동으로 실행")
async def test_fetch_website_content():
    """웹 페이지 콘텐츠 가져오기 테스트"""
    success, content = await fetch_website_content("https://www.example.com")
    assert success
    assert content is not None
    assert "html" in content.lower()

# 웹사이트 분석 테스트
@pytest.mark.asyncio
@pytest.mark.skip(reason="실제 웹사이트에 접근하므로 필요시 수동으로 실행")
async def test_analyze_website():
    """웹사이트 분석 테스트"""
    success, results = await analyze_website("https://www.example.com")
    assert success
    assert results is not None
    assert "metadata" in results
    assert "colors" in results

if __name__ == "__main__":
    # 테스트 실행
    pytest.main(["-xvs", __file__]) 