"""
Tests for GET /api/v1/compatibility/* endpoints.
Issue #85 — Expose Compatibility Matrices via REST API.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
BASE = "/api/v1/compatibility"


# ── Summary ───────────────────────────────────────────────────────────────────

def test_summary_returns_all_three_matrices():
    res = client.get(BASE)
    assert res.status_code == 200
    body = res.json()
    assert "matrices" in body
    assert set(body["matrices"].keys()) == {"cuda", "rocm", "python"}


# ── CUDA ──────────────────────────────────────────────────────────────────────

def test_cuda_matrix_returns_data():
    res = client.get(f"{BASE}/cuda")
    assert res.status_code == 200
    body = res.json()
    assert body["matrix"] == "cuda"
    assert body["count"] > 0
    assert "data" in body
    assert "supported_versions" in body


def test_cuda_known_version_returns_entry():
    res = client.get(f"{BASE}/cuda/11.8")
    assert res.status_code == 200
    body = res.json()
    assert body["cuda_version"] == "11.8"
    assert "min_driver_linux" in body
    assert "min_driver_windows" in body
    assert "cudnn_versions" in body
    assert "supported_archs" in body


def test_cuda_unknown_version_returns_404():
    res = client.get(f"{BASE}/cuda/99.9")
    assert res.status_code == 404
    body = res.json()
    assert body["detail"]["error"]["code"] == "CUDA_VERSION_NOT_FOUND"
    assert "supported_versions" in body["detail"]["error"]


def test_cuda_framework_support_map():
    res = client.get(f"{BASE}/cuda/frameworks")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "torch" in body["data"]


# ── ROCm ──────────────────────────────────────────────────────────────────────

def test_rocm_matrix_returns_data():
    res = client.get(f"{BASE}/rocm")
    assert res.status_code == 200
    body = res.json()
    assert body["matrix"] == "rocm"
    assert body["count"] > 0


def test_rocm_known_version_returns_entry():
    res = client.get(f"{BASE}/rocm/6.0.0")
    assert res.status_code == 200
    body = res.json()
    assert body["rocm_version"] == "6.0.0"
    assert "supported_gpus" in body
    assert "min_driver_linux" in body


def test_rocm_unknown_version_returns_404():
    res = client.get(f"{BASE}/rocm/99.9")
    assert res.status_code == 404
    assert res.json()["detail"]["error"]["code"] == "ROCM_VERSION_NOT_FOUND"


# ── Python ────────────────────────────────────────────────────────────────────

def test_python_matrix_returns_data():
    res = client.get(f"{BASE}/python")
    assert res.status_code == 200
    body = res.json()
    assert body["matrix"] == "python"
    assert "torch" in body["data"]


def test_python_known_framework_returns_entries():
    res = client.get(f"{BASE}/python/torch")
    assert res.status_code == 200
    body = res.json()
    assert body["framework"] == "torch"
    assert body["count"] > 0
    assert isinstance(body["data"], list)


def test_python_known_framework_version_returns_entry():
    res = client.get(f"{BASE}/python/torch/2.1.0")
    assert res.status_code == 200
    body = res.json()
    assert body["version"] == "2.1.0"
    assert "min_python" in body
    assert "max_python" in body
    assert "supported_python" in body
    assert "supported_cuda" in body


def test_python_unknown_framework_returns_404():
    res = client.get(f"{BASE}/python/unicorn")
    assert res.status_code == 404
    assert res.json()["detail"]["error"]["code"] == "FRAMEWORK_NOT_FOUND"


def test_python_unknown_version_returns_404():
    res = client.get(f"{BASE}/python/torch/0.0.0")
    assert res.status_code == 404
    assert res.json()["detail"]["error"]["code"] == "FRAMEWORK_VERSION_NOT_FOUND"
