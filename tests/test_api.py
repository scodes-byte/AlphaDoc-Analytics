import io
import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ["GEMINI_API_KEY"] = ""

import app as backend_app  # noqa: E402

client = TestClient(backend_app.app)


def test_health_reports_offline_mode():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["llm_enabled"] is False


def test_demo_uses_real_tesla_reports():
    response = client.get("/api/demo")
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Tesla"
    assert len(data["historical"]) == 8
    assert data["historical"][-1]["period"] == "Q4 2024"
    assert data["historical"][-1]["revenue"] == 25707
    assert data["next_period"] == "Q1 2025"
    fc = data["forecasts"]["revenue"]
    assert fc["lower_95"] <= fc["predicted"] <= fc["upper_95"]
    assert "image_b64" not in data


def test_chat_after_demo_routes_to_kpi_agent():
    client.get("/api/demo")
    data = client.post("/api/chat", json={"message": "What is the revenue forecast?"}).json()
    log = " ".join(data["thought_log"])
    assert "Routed target scope: KPI Analytics Agent" in log
    assert "Risk Specialist Agent" not in log  # only the relevant specialist runs
    assert "Q1 2025" in data["response"]


def test_routing_uses_whole_words():
    client.get("/api/demo")
    log = " ".join(client.post("/api/chat", json={"message": "It seems fine"}).json()["thought_log"])
    assert "Routed target scope: Multimodal Vision Agent" not in log  # "seems" must not match "see"


def test_upload_real_pdf():
    path = os.path.join(ROOT, "real_datasets", "TSLA_Q3_2024_Update.pdf")
    with open(path, "rb") as f:
        response = client.post("/api/upload", files={"file": ("TSLA_Q3_2024_Update.pdf", f, "application/pdf")})
    assert response.status_code == 200
    data = response.json()
    assert [h["period"] for h in data["historical"]][-1] == "Q3 2024"
    assert data["extraction_mode"]["kpi_values_found_in_source_text"] == 1.0


def test_upload_rejects_bad_extension():
    response = client.post("/api/upload", files={"file": ("notes.txt", io.BytesIO(b"hi"), "text/plain")})
    assert response.status_code == 400


def test_upload_path_traversal_name_is_not_used_as_path():
    response = client.post("/api/upload", files={"file": ("../../evil.pdf", io.BytesIO(b"not a pdf"), "application/pdf")})
    assert response.status_code in (422, 500)
    assert not os.path.exists(os.path.join(ROOT, "evil.pdf"))
    assert os.listdir(backend_app.UPLOAD_DIR) == []


def test_image_without_api_key_gives_clear_error():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buf, format="PNG")
    buf.seek(0)
    response = client.post("/api/upload", files={"file": ("chart.png", buf, "image/png")})
    assert response.status_code == 422
    assert "GEMINI_API_KEY" in response.json()["detail"]


@pytest.mark.parametrize("message", ["", "x" * 2001])
def test_chat_validates_message_length(message):
    assert client.post("/api/chat", json={"message": message}).status_code == 422
