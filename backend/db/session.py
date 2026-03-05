"""Session dependency for FastAPI. Yields a DB session and closes it after request."""
from collections.abc import Generator

from sqlalchemy.orm import Session

from db.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session; ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
