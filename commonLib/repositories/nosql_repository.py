from typing import Generic, Type, TypeVar, List
from bson.objectid import ObjectId
from pydantic.main import BaseModel
from pymongo.cursor import Cursor
from pymongo.database import Database
from pymongo.collection import Collection

from commonLib.models.mongo_base_class import MongoBase

ModelType = TypeVar("ModelType", bound=MongoBase)






class BaseMongo(Generic[ModelType]):
    def __init__(self, db: Database, model: Type[ModelType]):
        self.model = model
        self.collection: Collection = db.get_collection(model.__collectionname__)

    def get(self, object_id: str) -> Optional[ModelType]:
        document = self.collection.find_one({"_id": ObjectId(object_id)})
        return self.model(**document) if document else None

    def get_multiple(self, conditions: dict = {}) -> List[ModelType]:
        documents = self.collection.find(conditions)
        return [self.model(**doc) for doc in documents]

    def create(self, obj_in: BaseModel) -> ModelType:
        obj_in_dict = obj_in.dict(by_alias=True)
        result = self.collection.insert_one(obj_in_dict)
        return self.get(str(result.inserted_id))

    def update(self, object_id: str, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> Optional[ModelType]:
        if isinstance(obj_in, dict):
            update_data = {"$set": obj_in}
        else:
            update_data = {"$set": obj_in.dict(exclude_unset=True)}
        self.collection.update_one({"_id": ObjectId(object_id)}, update_data)
        return self.get(object_id)

    def delete(self, object_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(object_id)})
        return result.deleted_count > 0
