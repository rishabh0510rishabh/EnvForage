"""
Seed service — loads YAML fixtures into the database.
Run once on startup (idempotent via upsert logic).

Usage:
    python -m app.services.seed_service
"""

import asyncio
import logging
from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.profile import EnvironmentProfile, ProfilePackage
from app.schemas.seed_profile import ProfileSeedSchema, validate_logical_consistency
from app.services.sync_service import seed_compatibility_matrices

SEEDS_DIR = Path(__file__).parent.parent.parent / "seeds"
logger = logging.getLogger(__name__)


def _format_validation_errors(exc: ValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        parts.append(f"{location}: {error['msg']}")
    return "; ".join(parts)


def _profile_ref(raw: object, index: int) -> str:
    if isinstance(raw, dict):
        slug = raw.get("slug")
        if slug:
            return str(slug)
    return f"index={index}"


async def seed_profiles(db: AsyncSession) -> None:
    """Insert or skip environment profiles from profiles.yaml."""
    profiles_file = SEEDS_DIR / "profiles.yaml"
    if not profiles_file.exists():
        logger.warning("profiles.yaml not found at %s", profiles_file)
        return

    try:
        raw_text = profiles_file.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_text)
    except (OSError, UnicodeDecodeError) as exc:
        logger.error("Failed to read profiles.yaml: %s", exc)
        return
    except yaml.YAMLError as exc:
        logger.error("Failed to parse profiles.yaml: %s", exc)
        return

    if data is None:
        logger.warning("profiles.yaml is empty")
        return

    if not isinstance(data, dict):
        logger.error(
            "Invalid profiles.yaml: expected mapping at root, got %s",
            type(data).__name__,
        )
        return

    profiles_data = data.get("profiles")
    if not isinstance(profiles_data, list):
        logger.error("Invalid profiles.yaml: 'profiles' must be a list")
        return

    seeded = 0
    skipped = 0
    invalid = 0

    for index, raw_profile in enumerate(profiles_data):
        profile_ref = _profile_ref(raw_profile, index)
        try:
            profile_data = ProfileSeedSchema.model_validate(raw_profile)
        except ValidationError as exc:
            logger.warning(
                "Skipping profile '%s': %s",
                profile_ref,
                _format_validation_errors(exc),
            )
            invalid += 1
            continue

        logical_errors = validate_logical_consistency(profile_data)
        if logical_errors:
            for err in logical_errors:
                logger.warning(
                    "Skipping profile '%s' (logical error): %s",
                    profile_ref,
                    err,
                )
            invalid += 1
            continue

        result = await db.execute(
            select(EnvironmentProfile).where(
                EnvironmentProfile.slug == profile_data.slug
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            skipped += 1
            continue

        # FIX: Wrap profile + package inserts in a nested transaction (savepoint).
        # If any package insert fails, the entire profile is rolled back atomically,
        # preventing partial/corrupted rows from being committed to the database.
        try:
            async with db.begin_nested():
                profile = EnvironmentProfile(
                    slug=profile_data.slug,
                    name=profile_data.name,
                    description=profile_data.description,
                    tags=profile_data.tags,
                    os_support=profile_data.os_support,
                    cuda_required=profile_data.cuda_required,
                    python_versions=profile_data.python_versions,
                    cuda_versions=profile_data.cuda_versions,
                    status=profile_data.status,
                    last_validated=profile_data.last_validated,
                )
                db.add(profile)
                await db.flush()

                for pkg in profile_data.packages:
                    db.add(
                        ProfilePackage(
                            profile_id=profile.id,
                            package_name=pkg.name,
                            version_spec=pkg.version_spec,
                            cuda_variant=pkg.cuda_variant,
                            is_optional=pkg.is_optional,
                            install_order=pkg.install_order,
                        )
                    )

            seeded += 1
        except Exception as exc:
            logger.error("Failed to seed profile '%s': %s", profile_data.slug, exc)
            invalid += 1

    await db.commit()
    logger.info(
        "Profiles: %d seeded, %d already existed, %d invalid (skipped).",
        seeded,
        skipped,
        invalid,
    )


async def run_all_seeds() -> None:
    async with AsyncSessionLocal() as db:
        logger.info("Running database seeds...")
        await seed_compatibility_matrices(db)
        await seed_profiles(db)
        logger.info("Done.")


if __name__ == "__main__":
    from app.core.logging import setup_logging

    setup_logging()
    asyncio.run(run_all_seeds())
