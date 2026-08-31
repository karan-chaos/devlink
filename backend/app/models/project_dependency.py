import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class ProjectDependency(Base):
    """An external dependency tracked for a project."""

    __tablename__ = "project_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)
    current_version = Column(String(50), nullable=True)
    latest_version = Column(String(50), nullable=True)
    category = Column(
        String(50), nullable=False, default="other", index=True
    )  # frontend | backend | database | devops | testing | utility | other
    description = Column(Text, nullable=True)
    homepage_url = Column(String(500), nullable=True)
    is_critical = Column(Boolean, default=False, nullable=False)
    is_outdated = Column(Boolean, default=False, nullable=False, index=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    author = relationship("User", backref="added_dependencies")
    project = relationship("Project", backref="dependencies")
    version_history = relationship(
        "DependencyVersionLog",
        back_populates="dependency",
        cascade="all, delete-orphan",
        order_by="DependencyVersionLog.changed_at.desc()",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_dependency_name"),
    )


class DependencyVersionLog(Base):
    """Tracks version changes over time for auditing."""

    __tablename__ = "dependency_version_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dependency_id = Column(
        String(36),
        ForeignKey("project_dependencies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_version = Column(String(50), nullable=True)
    new_version = Column(String(50), nullable=True)
    changed_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    dependency = relationship("ProjectDependency", back_populates="version_history")
