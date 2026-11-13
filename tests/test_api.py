from fastapi.testclient import TestClient
from make_synthetic_receipt import make_receipt
from test_extractors import FakeExtractor

from visibon import api
from visibon.preprocess import encode_jpeg


def test_extract_endpoint(monkeypatch):
    monkeypatch.setattr(api, "get_extractor", lambda *_a, **_k: FakeExtractor())
    client = TestClient(api.app)
    files = {"file": ("struk.jpg", encode_jpeg(make_receipt()), "image/jpeg")}
    resp = client.post("/extract", files=files)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["receipt"]["merchant"] == "Warung Bu Siti"
    assert body["validation"]["is_valid"] is True


def test_extract_rejects_non_image():
    client = TestClient(api.app)
    resp = client.post("/extract", files={"file": ("x.txt", b"bukan gambar", "text/plain")})
    assert resp.status_code == 400
