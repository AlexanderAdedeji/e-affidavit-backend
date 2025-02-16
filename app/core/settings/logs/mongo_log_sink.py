
import os

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

# Initialize MongoDB variables as None for now.
client = None
db_client = None
log_collection = None


def init_mongo_sink():
    # Local import to avoid circular dependency
    from app.core.settings.configurations import settings

    global client, db_client, log_collection
    MONGO_URL = settings.MONGO_DB_URL
    MONGO_DB = settings.MONGO_DB_NAME
    client = AsyncIOMotorClient(MONGO_URL)
    db_client = client.get_database(MONGO_DB)
    log_collection = db_client["logs"]
    logger.info("Successfully connected to MongoDB for logging. for logs")


try:
    init_mongo_sink()
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")


def mongo_sink(message):
    """
    A custom Loguru sink that writes log records into MongoDB.
    """
    record = message.record
    log_doc = {
        "time": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "name": record["name"],
        "function": record["function"],
        "line": record["line"],
        "process": record["process"],
        "thread": record["thread"],
        "extra": record.get("extra", {}),
    }
    try:

        log_collection.insert_one(log_doc)
    except Exception as e:
        logger.error(f"Failed to write log to MongoDB: {e}")
