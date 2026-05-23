import asyncio

from app.database import AsyncSessionLocal
from app.services.profile_service import get_profile_by_slug


async def main():
    async with AsyncSessionLocal() as db:
        profile = await get_profile_by_slug(db, "pytorch-cuda")
        print("PROFILE:", profile)
        if profile:
            from app.schemas.profile import ProfileDetailSchema
            print(ProfileDetailSchema.model_validate(profile))

if __name__ == "__main__":
    asyncio.run(main())
