from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings.configurations import settings


url = settings.MONGO_DB_URL
client = AsyncIOMotorClient(url)
db_client = client.get_database("E-Affidavit-dev")

# You can also access a specific collection like this:
template_collection = db_client["templates"]
document_collection = db_client["documents"]


