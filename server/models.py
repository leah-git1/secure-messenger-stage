"""
models.py — Database tables as Python classes (SQLAlchemy ORM).

╔══════════════════════════════════════════════╗
║  YOUR TASK: fill in the two table classes.   ║
╚══════════════════════════════════════════════╝

WHAT IS AN ORM?
  Instead of writing raw SQL like:
      CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, ...)
  you write a Python class and SQLAlchemy creates the table for you.
  Reading and writing rows becomes reading and writing Python objects.

WHAT IS SQLITE?
  A database that lives in a single file (messenger.db).
  No server to install, no configuration — just a file.
  Perfect for development and learning.

THE TWO TABLES YOU NEED:

  User — one row per registered user
    id            : integer, primary key
    username      : string, must be unique (no two users with the same name)
    password_hash : string  (NEVER store the plain password — only the hash)
    created_at    : datetime, set automatically when the row is created

  Message — one row per sent message
    id         : integer, primary key
    sender     : string  (the username of who sent it)
    recipient  : string  (the username of who should receive it)
    ciphertext : text    (the AES-encrypted content — NEVER store plain text)
    created_at : datetime, set automatically when the row is created

USEFUL REFERENCE:
  Mapped column types: String, Text, DateTime
  mapped_column options: primary_key=True, index=True, unique=True, nullable=False
  Auto-set timestamp: default=lambda: datetime.now(timezone.utc)
"""

from datetime import datetime, timezone
from sqlalchemy import create_engine, func, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# 1. הגדרת ה-Base - ממנו יורשות כל הטבלאות
class Base(DeclarativeBase):
    pass

# ---------------------------------------------------------------------------
# TODO 1 — Define the User table
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # חותמת זמן ליצירת המשתמש
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )

# ---------------------------------------------------------------------------
# TODO 2 — Define the Message table
# ---------------------------------------------------------------------------
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sender: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(String(50), nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    
    # חותמת זמן למשלוח ההודעה (חשוב מאוד ל-Stage 2 של ה-Realtime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

# ---------------------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------------------
DATABASE_URL = "sqlite:///./messenger.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    echo=False
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    """
    FastAPI dependency — opens a DB session for one request, closes it after.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Creates all tables in the database if they don't exist yet."""
    Base.metadata.create_all(bind=engine)