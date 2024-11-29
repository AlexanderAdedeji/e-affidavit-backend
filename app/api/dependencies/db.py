from typing import Generator
from sqlalchemy.orm import Session
from app.database.sessions.session import SessionLocal
import logging

logger = logging.getLogger(__name__)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()
        logger.debug("Database session closed.")
