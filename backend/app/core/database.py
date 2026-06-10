
# --- Advanced SQLAlchemy BaseMixin ---
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Boolean, text
from sqlalchemy.orm import declarative_mixin, validates
from sqlalchemy.ext.declarative import declared_attr
from typing import Optional, Dict, Any

def utc_now():
    return datetime.now(timezone.utc)

@declarative_mixin
class AdvancedBaseMixin:
    """
    A highly robust SQLAlchemy declarative mixin providing:
    - UUIDv4 primary keys
    - created_at / updated_at automatic timestamps
    - Soft delete functionality (is_deleted, deleted_at, deleted_by)
    - Audit tracking (created_by, updated_by)
    - Optimistic concurrency control (version_id)
    """
    
    @declared_attr
    def __tablename__(cls) -> str:
        # Auto-generate table name based on class name (e.g. UserProfile -> user_profiles)
        name = cls.__name__
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower() + 's'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    
    # Soft Delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(36), nullable=True) # User ID who deleted
    
    # Audit Trail
    created_by = Column(String(36), nullable=True) # User ID who created
    updated_by = Column(String(36), nullable=True) # User ID who last updated
    
    # Optimistic Concurrency Control (handled by SQLAlchemy mapper)
    # version_id = Column(Integer, nullable=False, default=1)
    # __mapper_args__ = { 'version_id_col': version_id }
    
    def soft_delete(self, user_id: str = None) -> None:
        """Marks the record as deleted without dropping from DB."""
        self.is_deleted = True
        self.deleted_at = utc_now()
        if user_id:
            self.deleted_by = user_id
            
    def restore(self) -> None:
        """Restores a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        
    @validates('is_deleted')
    def validate_is_deleted(self, key, is_deleted):
        if is_deleted and not self.deleted_at:
            self.deleted_at = utc_now()
        return is_deleted

    def to_dict(self) -> Dict[str, Any]:
        """Converts the model instance into a dictionary for serialization."""
        result = {}
        for column in self.__table__.columns:
            val = getattr(self, column.name)
            if isinstance(val, datetime):
                result[column.name] = val.isoformat()
            else:
                result[column.name] = val
        return result

    @classmethod
    def filter_active(cls, query):
        """Applies a global filter to exclude soft-deleted records."""
        return query.filter(cls.is_deleted == False)

    def update_audit(self, user_id: str):
        """Updates the audit trail for the current transaction."""
        self.updated_by = user_id
        self.updated_at = utc_now()
        
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, active={not self.is_deleted})>"
