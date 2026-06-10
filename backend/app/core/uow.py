import abc
import logging
from typing import Type, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

logger = logging.getLogger("UnitOfWork")

class AbstractRepository(abc.ABC):
    """Base repository interface for the UoW pattern."""
    def __init__(self, session: AsyncSession):
        self.session = session

    @abc.abstractmethod
    async def add(self, entity: Any):
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, id: Any) -> Optional[Any]:
        raise NotImplementedError

class AbstractUnitOfWork(abc.ABC):
    """
    Abstract base class defining the Unit of Work interface.
    Ensures that all repositories share a single database transaction.
    """
    # Repositories would be defined here as properties
    # profiles: ProfileRepository
    # webhooks: WebhookRepository
    
    async def __aenter__(self) -> 'AbstractUnitOfWork':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    @abc.abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self):
        raise NotImplementedError

class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    Concrete implementation of the UoW pattern using SQLAlchemy AsyncSession.
    Provides complete isolation and automatic rollback handling.
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self) -> 'SQLAlchemyUnitOfWork':
        self.session = self.session_factory()
        # Initialize concrete repositories here passing self.session
        return super().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                logger.error(f"UoW aborting transaction due to: {exc_val}")
                await self.rollback()
            else:
                await self.commit()
        finally:
            if self.session:
                await self.session.close()

    async def commit(self):
        if self.session:
            try:
                await self.session.commit()
                logger.debug("UoW transaction committed successfully.")
            except Exception as e:
                logger.error(f"UoW commit failed: {e}")
                await self.rollback()
                raise

    async def rollback(self):
        if self.session:
            logger.debug("UoW transaction rolled back.")
            await self.session.rollback()

@asynccontextmanager
async def transaction(session_factory) -> SQLAlchemyUnitOfWork:
    """
    Syntactic sugar for using the UoW pattern cleanly in FastAPI routes.
    
    Usage:
        async with transaction(AsyncSessionLocal) as uow:
            uow.profiles.add(profile)
            # automatically commits on exit
    """
    uow = SQLAlchemyUnitOfWork(session_factory)
    async with uow:
        yield uow
