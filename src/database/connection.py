"""
Database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from loguru import logger

from config.settings import get_settings
from src.database.models import Base

# Global engine and session factory
_engine = None
_SessionLocal = None


def init_db():
    """Initialize database connection and create tables"""
    global _engine, _SessionLocal

    settings = get_settings()

    # Create engine
    _engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,
        max_overflow=20,
        echo=settings.debug_mode,  # Log SQL queries in debug mode
    )

    # Create session factory
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine
    )

    # Create all tables
    Base.metadata.create_all(bind=_engine)

    logger.info("Database initialized successfully")


def get_engine():
    """Get database engine"""
    if _engine is None:
        init_db()
    return _engine


def get_session_factory():
    """Get session factory"""
    if _SessionLocal is None:
        init_db()
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup.

    Usage:
        with get_db_session() as session:
            user = session.query(User).first()
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.

    Usage in FastAPI:
        @app.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db():
    """Close database connections"""
    global _engine
    if _engine:
        _engine.dispose()
        logger.info("Database connections closed")
