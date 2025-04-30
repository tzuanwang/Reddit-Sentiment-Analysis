from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_analyze_endpoint():
    sample_text = {"text": "Bitcoin is amazing, I love it!"}
    response = client.post("/analyze", json=sample_text)

    assert response.status_code == 200
    result = response.json()

    assert "sentiment" in result
    assert "emotion" in result
    assert "hate" in result

    for category in ["sentiment", "emotion", "hate"]:
        assert isinstance(result[category], dict)
        assert all(isinstance(v, float) for v in result[category].values())
