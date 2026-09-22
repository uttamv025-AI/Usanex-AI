from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    receiver_user_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False
    )

    sender_user_id: Mapped[str | None] = mapped_column(
        String(50),
        index=True,
        nullable=True
    )

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    connection_request_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    verification_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
