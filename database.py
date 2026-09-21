import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    String,
    DateTime,
    Boolean,
    Integer,
    Text
)

from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker,
    Mapped,
    mapped_column
)


# ============================================================
# DATABASE URL
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not configured."
    )

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )


# ============================================================
# ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# ============================================================
# BASE
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# USERS
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    mobile: Mapped[str] = mapped_column(
        String(15),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    profile_photo: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )


# ============================================================
# USER PRESENCE
# ============================================================
# Online / Offline / Last Seen
#
# Important:
# Existing users table ko modify nahi kar rahe.
# Ye separate table automatically create hogi.
# ============================================================

class UserPresence(Base):
    __tablename__ = "user_presence"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False
    )

    is_online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# ============================================================
# OTP VERIFICATION
# ============================================================

class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    identifier: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False
    )

    otp: Mapped[str] = mapped_column(
        String(6),
        nullable=False
    )

    purpose: Mapped[str] = mapped_column(
        String(30),
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


# ============================================================
# CONNECTION REQUESTS
# ============================================================

class ConnectionRequest(Base):
    __tablename__ = "connection_requests"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    requester_user_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    target_user_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# ============================================================
# CONNECTION VERIFICATION CODE
# ============================================================

class ConnectionCode(Base):
    __tablename__ = "connection_codes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    requester_user_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    target_user_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    code: Mapped[str] = mapped_column(
        String(6),
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    receiver_user_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    sender_user_id: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    type: Mapped[str] = mapped_column(
        String(40),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(150),
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
        String(6),
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


# ============================================================
# VERIFIED CONNECTIONS
# ============================================================

class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_a_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    user_b_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# ============================================================
# CHAT MESSAGES
# ============================================================

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    sender_user_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    receiver_user_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    message_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        nullable=False
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
        nullable=False
    )

# ============================================================
# STATUS
# ============================================================

class Status(Base):
    __tablename__ = "statuses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )

    media_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    media_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        index=True,
        nullable=False
    )


# ============================================================
# CREATE ALL TABLES
# ============================================================

Base.metadata.create_all(
    bind=engine
)
