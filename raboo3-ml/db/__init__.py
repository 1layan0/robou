"""Database package: engine and session. الجداول المعتمدة: schema_aggregate (خمس جداول)."""
from db.base import Base, engine, SessionLocal
from db.session import get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
