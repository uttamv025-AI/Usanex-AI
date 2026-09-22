from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    Index,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Status(Base):
    __tablename__ = "statuses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False
    )

    media_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )

    media_type: Mapped[str] = mapped_column(
        String(20),
        default="image",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )


class StatusView(Base):
    __tablename__ = "status_views"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    status_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False
    )

    viewer_user_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False
    )

    viewed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "status_id",
            "viewer_user_id",
            name="uq_status_viewer"
        ),
        Index(
            "ix_status_views_status_viewer",
            "status_id",
            "viewer_user_id"
        ),
    )
