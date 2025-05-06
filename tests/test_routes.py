import pytest
from fastapi.testclient import TestClient
from src.main import create_application

@pytest.fixture
def client():
    app = create_application()
    return TestClient(app)

def test_homepage(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "홈페이지 클론 기획서" in response.text

def test_api_analyze(client):
    response = client.post("/api/analyze", json={"url": "https://example.com"})
    assert response.status_code == 200
    assert "result_id" in response.json() or "result" in response.json() 