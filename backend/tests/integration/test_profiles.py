import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.main import app
from app.models.profile import EnvironmentProfile

pytestmark = pytest.mark.asyncio

# Must match the ADMIN_API_KEY set in conftest.py os.environ.setdefault
ADMIN_HEADERS = {"X-Admin-API-Key": "test-admin-key-for-ci"}


@pytest.fixture
async def client(db_session_factory):
    """Provide an AsyncClient for testing FastAPI routes, overriding the DB dependency."""

    async def _get_db_override():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    del app.dependency_overrides[get_db]


async def test_profile_crud_lifecycle(client, db_session):
    """
    Integration test for the full CRUD lifecycle of an environment profile.
    1. Create profile
    2. Read profile
    3. Update/List profiles
    4. Delete profile
    5. Verify deleted profile is not accessible
    """
    profile_slug = "test-ml-cuda"
    profile_data = {
        "slug": profile_slug,
        "name": "Test ML CUDA Profile",
        "description": "An environment profile for PyTorch ML testing",
        "tags": ["ml", "cuda", "pytorch"],
        "os_support": ["LINUX", "WSL"],
        "cuda_required": True,
        "python_versions": ["3.10", "3.11"],
        "cuda_versions": ["12.1"],
        "packages": [
            {
                "package_name": "torch",
                "version_spec": "==2.3.0",
                "cuda_variant": "cu121",
                "is_optional": False,
                "install_order": 1,
            },
            {
                "package_name": "torchvision",
                "version_spec": "==0.18.0",
                "cuda_variant": "cu121",
                "is_optional": True,
                "install_order": 2,
            },
        ],
    }

    # ──── 1. CREATE ────
    create_response = await client.post(
        "/api/v1/profiles", json=profile_data, headers=ADMIN_HEADERS
    )
    assert create_response.status_code == 201
    created_profile = create_response.json()
    assert created_profile["slug"] == profile_slug
    assert created_profile["name"] == "Test ML CUDA Profile"
    assert created_profile["cuda_required"] is True
    assert len(created_profile["packages"]) == 2
    assert created_profile["packages"][0]["package_name"] == "torch"
    assert created_profile["packages"][1]["is_optional"] is True

    # Verify state in DB directly
    db_result = await db_session.execute(
        select(EnvironmentProfile)
        .options(selectinload(EnvironmentProfile.packages))
        .where(EnvironmentProfile.slug == profile_slug)
    )
    db_profile = db_result.scalar_one_or_none()
    assert db_profile is not None
    assert db_profile.name == "Test ML CUDA Profile"
    assert len(db_profile.packages) == 2

    # ──── 2. READ (Single) ────
    get_response = await client.get(f"/api/v1/profiles/{profile_slug}")
    assert get_response.status_code == 200
    retrieved_profile = get_response.json()
    assert retrieved_profile["slug"] == profile_slug
    assert len(retrieved_profile["packages"]) == 2

    # ──── 3. LIST/FILTER ────
    list_response = await client.get("/api/v1/profiles?cuda_required=true")
    assert list_response.status_code == 200
    listed_profiles = list_response.json()["profiles"]
    assert any(p["slug"] == profile_slug for p in listed_profiles)

    # Filter with non-matching tag should not include our profile
    list_response_no_match = await client.get("/api/v1/profiles?tags=nonexistent")
    assert list_response_no_match.status_code == 200
    listed_no_match = list_response_no_match.json()["profiles"]
    assert not any(p["slug"] == profile_slug for p in listed_no_match)

    # ──── 4. DELETE ────
    delete_response = await client.delete(
        f"/api/v1/profiles/{profile_slug}", headers=ADMIN_HEADERS
    )
    assert delete_response.status_code == 204

    # ──── 5. VERIFY DELETED ────
    # Read single should now return 404
    get_after_delete = await client.get(f"/api/v1/profiles/{profile_slug}")
    assert get_after_delete.status_code == 404

    # List should not contain the deleted profile
    list_after_delete = await client.get("/api/v1/profiles")
    assert list_after_delete.status_code == 200
    listed_after = list_after_delete.json()["profiles"]
    assert not any(p["slug"] == profile_slug for p in listed_after)

    # Database state verification: verify soft-deleted (status="DELETED" and deleted_at is set)
    db_session.expire_all()  # clear session cache to fetch fresh from DB
    db_result_deleted = await db_session.execute(
        select(EnvironmentProfile).where(EnvironmentProfile.slug == profile_slug)
    )
    db_profile_deleted = db_result_deleted.scalar_one_or_none()
    assert db_profile_deleted is not None
    assert db_profile_deleted.deleted_at is not None
    assert db_profile_deleted.status == "DELETED"


async def test_create_duplicate_slug_conflict(client):
    """Test that creating a profile with an existing slug returns 409 Conflict."""
    profile_data = {
        "slug": "duplicate-slug",
        "name": "Original Profile",
        "os_support": ["LINUX"],
        "python_versions": ["3.10"],
    }

    # First creation
    res1 = await client.post(
        "/api/v1/profiles", json=profile_data, headers=ADMIN_HEADERS
    )
    assert res1.status_code == 201

    # Duplicate creation
    res2 = await client.post(
        "/api/v1/profiles", json=profile_data, headers=ADMIN_HEADERS
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]["error"]["message"].lower()


async def test_get_nonexistent_profile_returns_404(client):
    """Test that retrieving a nonexistent profile slug returns 404 Not Found."""
    response = await client.get("/api/v1/profiles/nonexistent-profile-slug")
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "PROFILE_NOT_FOUND"


async def test_delete_nonexistent_profile_returns_404(client):
    """Test that deleting a nonexistent profile slug returns 404 Not Found."""
    response = await client.delete(
        "/api/v1/profiles/nonexistent-profile-slug", headers=ADMIN_HEADERS
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "PROFILE_NOT_FOUND"


async def test_create_profile_without_admin_key_returns_401(client):
    """Test that POST /api/v1/profiles without an admin key returns 401."""
    profile_data = {
        "slug": "unauth-test",
        "name": "Unauth Test",
        "os_support": ["LINUX"],
        "python_versions": ["3.11"],
    }
    response = await client.post("/api/v1/profiles", json=profile_data)
    assert response.status_code == 401


async def test_delete_profile_without_admin_key_returns_401(client):
    """Test that DELETE /api/v1/profiles/{slug} without an admin key returns 401."""
    response = await client.delete("/api/v1/profiles/any-slug")
    assert response.status_code == 401


async def test_create_profile_with_wrong_admin_key_returns_401(client):
    """Test that POST /api/v1/profiles with an incorrect admin key returns 401."""
    wrong_headers = {"X-Admin-API-Key": "this-is-not-the-right-key"}
    profile_data = {
        "slug": "wrong-key-test",
        "name": "Wrong Key Test",
        "os_support": ["LINUX"],
        "python_versions": ["3.11"],
    }
    response = await client.post(
        "/api/v1/profiles", json=profile_data, headers=wrong_headers
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "INVALID_ADMIN_KEY"


async def test_delete_profile_with_wrong_admin_key_returns_401(client):
    """Test that DELETE /api/v1/profiles/{slug} with an incorrect admin key returns 401."""
    wrong_headers = {"X-Admin-API-Key": "this-is-not-the-right-key"}
    response = await client.delete("/api/v1/profiles/any-slug", headers=wrong_headers)
    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "INVALID_ADMIN_KEY"
