from typing import Dict, Any
from typing import Any, Dict
from pydantic import BaseModel
from datetime import datetime

from commonLib.models.mongo_base_class import MongoBase


class Templates(MongoBase):
    data: Dict[str, Any]


class Documents(MongoBase):
    data: Dict[str, Any]
