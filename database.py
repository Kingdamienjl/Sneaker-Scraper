"""
Database initialization and management utilities.
"""

import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base
from config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

# Synchronous engine for initial setup
sync_engine = create_engine(DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))

# Asynchronous engine for runtime operations
async_engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

def create_tables():
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

async def get_async_session():
    """Get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def init_database():
    """Initialize the database with tables and sample data."""
    logger.info("Initializing database...")
    create_tables()
    logger.info("Database initialization completed")

if __name__ == "__main__":
    init_database()