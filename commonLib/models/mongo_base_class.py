from typing import Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime




class MongoBase(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Document creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Document update timestamp")

    @classmethod
    def __collectionname__(cls):
        return cls.__name__.lower()
