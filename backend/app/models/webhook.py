import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Webhook(Base):
    __tablename__ = "webhooks"
    __table_args__ = (
        UniqueConstraint(
            "target_url",
            name="uq_webhooks_target_url",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_url = Column(String, nullable=False)
    secret = Column(String, nullable=False)
    events = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
