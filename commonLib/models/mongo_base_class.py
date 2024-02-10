from typing import Any, Dict
from pydantic import BaseModel
from datetime import datetime



class MongoBase(BaseModel):
    @classmethod
    def __collectionname__(cls):
        return cls.__name__.lower()