from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings.configurations import settings
from commonLib.utils.logger_config import logger


url = settings.MONGO_DB_URL
name = settings.MONGO_DB_NAME

# Initialize MongoDB Client
try:

    client = AsyncIOMotorClient(url)
    db_client = client.get_database(name)
    logger.info("Successfully connected to MongoDB.")
except:
    logger.error(f"Error connecting to MongoDB: {e}")


# Collections Access
template_collection = db_client["templates"]
document_collection = db_client["documents"]


