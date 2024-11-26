from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from commonLib.utils.logger_config import logger
from  app.core.settings.configurations import settings





url = settings.POSTGRES_DB_URL

try:
    engine = create_engine(url, pool_size=20, max_overflow=10, pool_timeout=3, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Successfully created PostgreSQL engine.")
except Exception as e:
    logger.error(f"Error creating PostgreSQL engine: {e}")






