
# --- Comprehensive DB Seeder ---
import logging
import random
from datetime import datetime, timedelta

try:
    from faker import Faker
except ImportError:
    Faker = None

# Mocks for ORM since models aren't fully defined in this snippet
class MockSession:
    async def execute(self, stmt): pass
    async def commit(self): pass
    async def rollback(self): pass
    async def close(self): pass

logger = logging.getLogger("DBSeeder")

class DatabaseSeeder:
    """
    A robust asynchronous database seeder utilizing Faker to generate
    highly realistic datasets for testing and development environments.
    Handles bulk inserts and foreign-key relationship mapping.
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory
        if Faker is not None:
            self.fake = Faker(['en_US'])
        else:
            logger.warning("Faker not installed. Falling back to basic mock data.")
            self.fake = None

    def _generate_mock_string(self, prefix: str) -> str:
        return f"{prefix}_{random.randint(1000, 9999)}"

    async def _clean_database(self, session):
        """Truncates tables before seeding to ensure idempotency."""
        logger.info("Cleaning database tables...")
        # Example TRUNCATE logic
        # await session.execute(text("TRUNCATE TABLE user_profiles, posts CASCADE"))
        pass

    async def _seed_users(self, session, count: int = 100) -> list[dict]:
        """Generates User profiles in bulk."""
        logger.info(f"Seeding {count} users...")
        users = []
        for _ in range(count):
            if self.fake:
                user = {
                    "id": self.fake.uuid4(),
                    "username": self.fake.user_name(),
                    "email": self.fake.unique.email(),
                    "first_name": self.fake.first_name(),
                    "last_name": self.fake.last_name(),
                    "is_active": True,
                    "created_at": self.fake.date_time_between(start_date='-1y', end_date='now')
                }
            else:
                user = {
                    "id": str(random.randint(10000, 99999)),
                    "username": self._generate_mock_string("user"),
                    "email": f"{self._generate_mock_string('email')}@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                    "is_active": True,
                    "created_at": datetime.utcnow()
                }
            users.append(user)

        # Example Bulk Insert
        # await session.execute(insert(User).values(users))
        return users

    async def _seed_posts(self, session, users: list[dict], count_per_user: int = 5):
        """Generates relational data (Posts) belonging to Users."""
        logger.info(f"Seeding posts for {len(users)} users...")
        posts = []
        for user in users:
            for _ in range(random.randint(0, count_per_user)):
                if self.fake:
                    post = {
                        "id": self.fake.uuid4(),
                        "user_id": user["id"],
                        "title": self.fake.catch_phrase(),
                        "content": self.fake.text(max_nb_chars=500),
                        "published": random.choice([True, False]),
                        "created_at": user["created_at"] + timedelta(days=random.randint(1, 30))
                    }
                else:
                    post = {
                        "id": str(random.randint(10000, 99999)),
                        "user_id": user["id"],
                        "title": self._generate_mock_string("Post"),
                        "content": "Mock content...",
                        "published": True,
                        "created_at": datetime.utcnow()
                    }
                posts.append(post)

        # Example Bulk Insert
        # await session.execute(insert(Post).values(posts))
        return posts

    async def run(self):
        """Executes the full database seeding orchestration."""
        session = self.session_factory()
        try:
            await self._clean_database(session)
            users = await self._seed_users(session, count=50)
            await self._seed_posts(session, users, count_per_user=10)
            await session.commit()
            logger.info("Database seeding completed successfully.")
        except Exception as e:
            await session.rollback()
            logger.error(f"Database seeding failed: {e}")
            raise
        finally:
            await session.close()
