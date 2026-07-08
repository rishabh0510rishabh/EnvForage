"""
Tests that functional endpoints reject unauthenticated requests.

Issue #1042 - functional routes were documented to require the CurrentUser
JWT dependency, but only /me actually enforced it. These tests assert that
requests without a Bearer token now get 401 from each newly-protected router.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
BASE = "/api/v1"


# ── GET endpoints: no token -> 401 ────────────────────────────────────────────


def test_compatibility_summary_requires_auth():
    res = client.get(f"{BASE}/compatibility")
    assert res.status_code == 401


def test_compatibility_cuda_requires_auth():
    res = client.get(f"{BASE}/compatibility/cuda")
    assert res.status_code == 401


def test_diagnose_status_requires_auth():
    res = client.get(f"{BASE}/diagnose/status/some-task-id")
    assert res.status_code == 401


def test_repair_templates_requires_auth():
    res = client.get(f"{BASE}/repair/templates")
    assert res.status_code == 401


def test_scripts_download_requires_auth():
    res = client.get(f"{BASE}/scripts/some-job-id/download")
    assert res.status_code == 401


# ── POST endpoints: no token -> 401 (auth runs before body validation) ────────


def test_troubleshoot_requires_auth():
    res = client.post(f"{BASE}/troubleshoot", json={})
    assert res.status_code == 401


def test_recommend_requires_auth():
    res = client.post(f"{BASE}/recommend", json={})
    assert res.status_code == 401


def test_verify_requires_auth():
    res = client.post(f"{BASE}/verify", json={})
    assert res.status_code == 401


def test_feedback_requires_auth():
    res = client.post(f"{BASE}/uninstall/feedback", json={})
    assert res.status_code == 401
