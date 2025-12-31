"""Database connection management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from loguru import logger

from src.config import Config

# Create base class for declarative models
Base = declarative_base()

# Create engine
engine = None
SessionLocal = None


def init_db():
    """Initialize database connection and create tables."""
    global engine, SessionLocal
    
    try:
        Config.validate()
        logger.info("Initializing database connection...")
        
        engine = create_engine(
            Config.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Import models to register them with Base
        from src.database.models import (
            Candidate,
            Job,
            Application,
            WhatIfScenario,
            OptimisationRecord
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_db():
    """Get database session."""
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Get a database session (for non-generator usage)."""
    if SessionLocal is None:
        init_db()
    return SessionLocal()
