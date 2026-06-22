"""Unit tests for database-backed compatibility matrix and sync service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.compatibility.models import PackageConstraint
from app.compatibility.resolver import (
    CompatibilityResolver,
    clear_compatibility_cache,
)
from app.database import get_db
from app.main import app
from app.models.matrix import CUDAMatrixEntry, PythonMatrixEntry, RocmMatrixEntry
from app.services.sync_service import (
    seed_compatibility_matrices,
    sync_nvidia_cuda_releases,
    sync_pypi_releases,
)

ADMIN_HEADERS = {"X-Admin-API-Key": "test-admin-key-for-ci"}


@pytest.fixture(autouse=True)
async def auto_clear_cache():
    await clear_compatibility_cache()
    yield
    await clear_compatibility_cache()


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


async def test_seeding_matrices(db_session):
    """Verify seeding compatibility matrices from static files works."""
    await seed_compatibility_matrices(db_session)

    # Check CUDA Matrix
    res_cuda = await db_session.execute(CUDAMatrixEntry.__table__.select())
    cuda_rows = res_cuda.all()
    assert len(cuda_rows) > 0

    # Check ROCm Matrix
    res_rocm = await db_session.execute(RocmMatrixEntry.__table__.select())
    rocm_rows = res_rocm.all()
    assert len(rocm_rows) > 0

    # Check Python Matrix
    res_py = await db_session.execute(PythonMatrixEntry.__table__.select())
    py_rows = res_py.all()
    assert len(py_rows) > 0


async def test_resolver_with_db_and_fallback(db_session):
    """Test CompatibilityResolver using database and safe fallback options."""
    await seed_compatibility_matrices(db_session)
    resolver = CompatibilityResolver()

    # 1. Resolve with database
    res = await resolver.resolve(
        packages=[PackageConstraint("torch", "2.1.2")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
        db=db_session,
    )
    assert res.packages[0].version == "2.1.2"
    assert res.packages[0].cuda_variant == "cu118"

    # 2. Resolve with db=None (static fallback)
    res_static = await resolver.resolve(
        packages=[PackageConstraint("torch", "2.1.2")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
        db=None,
    )
    assert res_static.packages[0].version == "2.1.2"

    # 3. Resolve with failing db (exception thrown during queries)
    await clear_compatibility_cache()
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("DB Connection Lost")
    res_error_fallback = await resolver.resolve(
        packages=[PackageConstraint("torch", "2.1.2")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
        db=mock_db,
    )
    assert res_error_fallback.packages[0].version == "2.1.2"


async def test_admin_matrix_crud_cuda(client, db_session):
    """Test CRUD operations on admin CUDA compatibility matrix."""
    cuda_data = {
        "cuda_version": "99.9",
        "min_driver_linux": "999.99",
        "min_driver_windows": "999.99",
        "cudnn_versions": ["9.9.9"],
        "supported_archs": ["sm_99"],
        "notes": "Test notes",
        "source_url": "http://test-cuda.com",
    }

    # 1. Create - POST without auth
    resp_unauth = await client.post("/api/v1/admin/matrix/cuda", json=cuda_data)
    assert resp_unauth.status_code == 401

    # 2. Create - POST with auth
    resp_create = await client.post(
        "/api/v1/admin/matrix/cuda", json=cuda_data, headers=ADMIN_HEADERS
    )
    assert resp_create.status_code == 201
    entry_id = resp_create.json()["id"]

    # 3. Read - GET compatibility lists
    resp_list = await client.get("/api/v1/compatibility/cuda")
    assert resp_list.status_code == 200
    assert "99.9" in resp_list.json()["data"]

    # 4. Update - PUT
    update_data = {"min_driver_linux": "888.88"}
    resp_update = await client.put(
        f"/api/v1/admin/matrix/cuda/{entry_id}", json=update_data, headers=ADMIN_HEADERS
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["min_driver_linux"] == "888.88"

    # 5. Delete - DELETE
    resp_delete = await client.delete(
        f"/api/v1/admin/matrix/cuda/{entry_id}", headers=ADMIN_HEADERS
    )
    assert resp_delete.status_code == 204

    # Verify deleted
    resp_list_after = await client.get("/api/v1/compatibility/cuda")
    assert "99.9" not in resp_list_after.json()["data"]


async def test_admin_matrix_crud_rocm(client, db_session):
    """Test CRUD operations on admin ROCm compatibility matrix."""
    rocm_data = {
        "rocm_version": "99.9.9",
        "min_driver_linux": "99.9",
        "supported_gpus": ["gfx999"],
        "notes": "ROCm notes",
        "source_url": "http://test-rocm.com",
    }

    # 1. Create - POST
    resp_create = await client.post(
        "/api/v1/admin/matrix/rocm", json=rocm_data, headers=ADMIN_HEADERS
    )
    assert resp_create.status_code == 201
    entry_id = resp_create.json()["id"]

    # 2. Read - GET compatibility
    resp_list = await client.get("/api/v1/compatibility/rocm")
    assert "99.9.9" in resp_list.json()["data"]

    # 3. Update - PUT
    update_data = {"min_driver_linux": "88.8"}
    resp_update = await client.put(
        f"/api/v1/admin/matrix/rocm/{entry_id}", json=update_data, headers=ADMIN_HEADERS
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["min_driver_linux"] == "88.8"

    # 4. Delete - DELETE
    resp_delete = await client.delete(
        f"/api/v1/admin/matrix/rocm/{entry_id}", headers=ADMIN_HEADERS
    )
    assert resp_delete.status_code == 204


async def test_admin_matrix_crud_python(client, db_session):
    """Test CRUD operations on admin Python/Framework compatibility matrix."""
    python_data = {
        "framework": "testframework",
        "version": "9.9.9",
        "min_python": "3.11",
        "max_python": "3.13",
        "supported_cuda": ["12.1"],
        "supported_rocm": [],
        "supported_python": ["3.11", "3.12", "3.13"],
    }

    # 1. Create - POST
    resp_create = await client.post(
        "/api/v1/admin/matrix/python", json=python_data, headers=ADMIN_HEADERS
    )
    assert resp_create.status_code == 201
    entry_id = resp_create.json()["id"]

    # 2. Read - GET compatibility
    resp_list = await client.get("/api/v1/compatibility/python/testframework")
    assert resp_list.status_code == 200
    assert resp_list.json()["data"][0]["version"] == "9.9.9"

    # 3. Update - PUT
    update_data = {"min_python": "3.12"}
    resp_update = await client.put(
        f"/api/v1/admin/matrix/python/{entry_id}",
        json=update_data,
        headers=ADMIN_HEADERS,
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["min_python"] == "3.12"

    # 4. Delete - DELETE
    resp_delete = await client.delete(
        f"/api/v1/admin/matrix/python/{entry_id}", headers=ADMIN_HEADERS
    )
    assert resp_delete.status_code == 204


async def test_pypi_and_cuda_sync(db_session):
    """Test syncing release information from PyPI and NVIDIA."""
    await seed_compatibility_matrices(db_session)

    mock_pypi_response = {
        "releases": {
            "3.0.0": [{"requires_python": ">=3.9"}],
            "2.5.0": [{"requires_python": ">=3.9"}],  # Already seeded, skipped
        }
    }

    mock_cuda_response = "<html><body>CUDA Toolkit 12.9.0 released!</body></html>"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        # Mock responses using MagicMock
        mock_pypi = MagicMock()
        mock_pypi.status_code = 200
        mock_pypi.json.return_value = mock_pypi_response

        mock_cuda = MagicMock()
        mock_cuda.status_code = 200
        mock_cuda.text = mock_cuda_response

        def get_side_effect(url, *args, **kwargs):
            if "pypi.org" in url:
                return mock_pypi
            if "nvidia.com" in url:
                return mock_cuda
            return MagicMock(status_code=404)

        mock_get.side_effect = get_side_effect

        await sync_pypi_releases(db_session)
        await sync_nvidia_cuda_releases(db_session)

    # Verify torch 3.0.0 was synced
    stmt = select(PythonMatrixEntry).where(
        (PythonMatrixEntry.framework == "torch")
        & (PythonMatrixEntry.version == "3.0.0")
    )
    res_torch = await db_session.execute(stmt)
    torch_entry = res_torch.scalars().first()
    assert torch_entry is not None
    assert torch_entry.min_python == "3.9"

    # Verify CUDA 12.9 was synced
    stmt_cuda = select(CUDAMatrixEntry).where(CUDAMatrixEntry.cuda_version == "12.9")
    res_cuda = await db_session.execute(stmt_cuda)
    cuda_entry = res_cuda.scalars().first()
    assert cuda_entry is not None

async def test_sync_pypi_preserves_same_run_inheritance(db_session):
    """Regression test for #1017.

    The closest-entry query was hoisted out of the per-version loop to avoid
    an O(N) full table scan per version. To keep behaviour identical, entries
    created during the same sync run are appended to the in-memory list so a
    later version can still inherit CUDA/ROCm from an earlier same-run version
    of the same major.minor. This test would fail if the query were naively
    hoisted without the in-memory append (2.9.5 would not see 2.9.0).
    """
    await seed_compatibility_matrices(db_session)

    # Two brand-new torch versions sharing major.minor 2.9, neither seeded.
    mock_pypi_response = {
        "releases": {
            "2.9.0": [{"requires_python": ">=3.9"}],
            "2.9.5": [{"requires_python": ">=3.9"}],
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_pypi = MagicMock()
        mock_pypi.status_code = 200
        mock_pypi.json.return_value = mock_pypi_response

        def get_side_effect(url, *args, **kwargs):
            if "pypi.org" in url:
                return mock_pypi
            return MagicMock(status_code=404)

        mock_get.side_effect = get_side_effect

        await sync_pypi_releases(db_session)

    # Both versions were inserted
    res = await db_session.execute(
        select(PythonMatrixEntry).where(
            (PythonMatrixEntry.framework == "torch")
            & (PythonMatrixEntry.version.in_(["2.9.0", "2.9.5"]))
        )
    )
    entries = {e.version: e for e in res.scalars().all()}
    assert "2.9.0" in entries
    assert "2.9.5" in entries

    # 2.9.5 must inherit the CUDA/ROCm of 2.9.0 (same major.minor), which was
    # created earlier in the SAME run — proving the in-memory append works.
    assert entries["2.9.5"].supported_cuda == entries["2.9.0"].supported_cuda
    assert entries["2.9.5"].supported_rocm == entries["2.9.0"].supported_rocm
