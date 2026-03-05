"""SQLAlchemy engine and declarative base. Sync MySQL via pymysql."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import settings

# Connection URL with charset for utf8mb4 (schema uses utf8mb4)
_url = (
    f"{settings.database_url}"
    "?charset=utf8mb4"
)

engine = create_engine(
    _url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
