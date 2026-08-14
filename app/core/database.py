import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

def get_engine():
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool
        return create_engine(db_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        conn = engine.connect()
        conn.close()
        return engine
    except Exception:
        fallback_url = "sqlite:///:memory:"
        from sqlalchemy.pool import StaticPool
        return create_engine(fallback_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
