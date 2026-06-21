
# --- Async SQLAlchemy Fixture System ---
import asyncio
import logging
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger("DBFixtures")

# Usually pulled from config
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """
    Creates an instance of the default event loop for the test session.
    Prevents 'Task attached to a different loop' errors in pytest-asyncio.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    """Creates a global async engine for the test session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True
    )

    # Ideally, we would create all tables here
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    yield engine

    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a highly isolated database session for a single test.
    Wraps the entire test execution in a transaction, and forces a rollback
    after the test completes, guaranteeing pristine state for the next test.
    Nested savepoints allow the test to commit internally without affecting the DB.
    """
    connection = await engine.connect()

    # Begin a global, non-committing transaction
    transaction = await connection.begin()

    # Bind an AsyncSession to the connection
    session_maker = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        class_=AsyncSession,
        join_transaction_mode="create_savepoint" # Crucial for isolation
    )

    session = session_maker()

    try:
        # Yield the session to the test
        yield session
    except Exception as e:
        logger.error(f"Test raised exception: {e}")
        raise
    finally:
        # Close the session
        await session.close()

        # Rollback the global transaction (undoes all test changes)
        await transaction.rollback()

        # Return connection to the pool
        await connection.close()

@pytest.fixture(scope="function")
async def mock_user_factory(db_session):
    """A factory fixture to generate mock database records dynamically within isolated tests."""
    async def _create_user(username: str = "testuser", email: str = "test@example.com"):
        # user = User(username=username, email=email)
        # db_session.add(user)
        # await db_session.commit()
        # await db_session.refresh(user)
        # return user
        return {"id": "mock_uuid", "username": username, "email": email}
    return _create_user
