from datetime import datetime

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    identifier: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False
    )

    otp: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
