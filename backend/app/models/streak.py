import uuid
from datetime import date, datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class StreakRecord(Base):
    """Tracks a single day of activity for a user on a project."""

    __tablename__ = "streak_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_date = Column(Date, nullable=False, index=True)
    activity_type = Column(
        String(50), nullable=False, default="general"
    )  # commit | issue | review | general
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", backref="streak_records")
    project = relationship("Project", backref="streak_records")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "project_id", "activity_date", name="uq_streak_day"
        ),
    )


class StreakSummary(Base):
    """Denormalized summary of a user's streak on a project for fast reads."""

    __tablename__ = "streak_summaries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    last_active_date = Column(Date, nullable=True)
    total_active_days = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", backref="streak_summaries")
    project = relationship("Project", backref="streak_summaries")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "project_id", name="uq_streak_summary_user_project"
        ),
    )
