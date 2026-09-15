import os
from datetime import datetime

from sqlalchemy import create_engine, String, DateTime, Boolean
from sqlalchemy.orm import (
DeclarativeBase,
sessionmaker,
Mapped,
mapped_column,
)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
raise RuntimeError(
"DATABASE_URL environment variable is not configured."
)

PostgreSQL + psycopg3

if DATABASE_URL.startswith("postgresql://"):
DATABASE_URL = DATABASE_URL.replace(
"postgresql://",
"postgresql+psycopg://",
1
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

============================================================

USER TABLE

============================================================

class User(Base):
tablename = "users"

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

============================================================

OTP TABLE

============================================================

class OTPVerification(Base):
tablename = "otp_verifications"

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

============================================================

CREATE TABLES

============================================================

Base.metadata.create_all(bind=engine)
