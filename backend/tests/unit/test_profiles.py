"""Unit tests for the PATCH /profiles/{slug} profile update endpoint."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import EnvironmentProfile, ProfilePackage
from app.schemas.profile import ProfileUpdateSchema
from app.services import profile_service

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_test_profile(
    db: AsyncSession, slug: str = "test-profile"
) -> EnvironmentProfile:
    """Insert a minimal active profile directly into the test DB."""
    profile = EnvironmentProfile(
        slug=slug,
        name="Test Profile",
        description="A profile for testing.",
        tags=["ml"],
        os_support=["LINUX"],
        cuda_required=False,
        python_versions=["3.11"],
        cuda_versions=None,
        status="ACTIVE",
    )
    pkg = ProfilePackage(
        package_name="numpy",
        version_spec=">=1.24",
        cuda_variant=None,
        is_optional=False,
        install_order=0,
    )
    profile.packages.append(pkg)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_profile_partial_fields(db_session: AsyncSession) -> None:
    """Only the supplied fields are changed; untouched fields are preserved."""
    await _create_test_profile(db_session, slug="patch-partial")

    update = ProfileUpdateSchema(name="Renamed Profile", tags=["ml", "updated"])
    result = await profile_service.update_profile(db_session, "patch-partial", update)

    assert result is not None
    assert result.name == "Renamed Profile"
    assert result.tags == ["ml", "updated"]
    # Unchanged fields are preserved
    assert result.description == "A profile for testing."
    assert result.os_support == ["LINUX"]
    assert result.cuda_required is False


@pytest.mark.asyncio
async def test_update_profile_replaces_packages(db_session: AsyncSession) -> None:
    """When packages are supplied the entire package list is replaced."""
    await _create_test_profile(db_session, slug="patch-packages")

    new_packages = [
        {
            "package_name": "torch",
            "version_spec": "==2.1.0",
            "cuda_variant": None,
            "is_optional": False,
            "install_order": 0,
        }
    ]
    update = ProfileUpdateSchema(packages=new_packages)  # type: ignore[arg-type]
    result = await profile_service.update_profile(db_session, "patch-packages", update)

    assert result is not None
    assert len(result.packages) == 1
    assert result.packages[0].package_name == "torch"


@pytest.mark.asyncio
async def test_update_profile_not_found(db_session: AsyncSession) -> None:
    """update_profile returns None for a slug that does not exist."""
    update = ProfileUpdateSchema(name="Ghost")
    result = await profile_service.update_profile(
        db_session, "nonexistent-slug", update
    )
    assert result is None


@pytest.mark.asyncio
async def test_update_profile_empty_body_is_noop(db_session: AsyncSession) -> None:
    """Sending an empty update body leaves the profile unchanged."""
    await _create_test_profile(db_session, slug="patch-noop")

    update = ProfileUpdateSchema()
    result = await profile_service.update_profile(db_session, "patch-noop", update)

    assert result is not None
    assert result.name == "Test Profile"
    assert result.description == "A profile for testing."
