from fastapi.testclient import TestClient
from pprint import pprint

from main import app

client = TestClient(app)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_route():
    response = client.post(
        "/api/route",
        headers={"X-Token": "coneofsilence"},
        json={"start_location_name": "樟葉駅", "prompt": "10km圏内のルートを提示してください。"},
    )
    assert response.status_code == 200
    pprint(response.json())
