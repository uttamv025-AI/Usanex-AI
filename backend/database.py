import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")


if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


# =========================================================
# IMPORT ALL MODELS
# =========================================================

from backend.models import (
    User,
    UserPresence,
    OTPVerification,
    ConnectionRequest,
    ConnectionCode,
    Connection,
    Notification,
    ChatMessage,
    Status,
    StatusView,
)


# =========================================================
# CREATE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)
