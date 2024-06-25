from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi import HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from commonLib.models.base_class import Base as BaseDeclarativeClass
from sqlalchemy.exc import IntegrityError

ModelType = TypeVar("ModelType", bound=BaseDeclarativeClass)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class Base(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:

        return db.query(self.model).filter(self.model.id == id).first()

    def exist(self, db: Session, id: Any) -> bool:
        data = self.get(db, id)
        return data if data else False

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def get_multi_by_ids(self, db: Session, *, ids: List[int]) -> List[ModelType]:
        in_condition = self.model.id.in_(ids)
        return db.query(self.model).filter(in_condition)

    def get_all(self, db: Session) -> List[ModelType]:
        return db.query(self.model).all()
    
    def get_count(self, db:Session)->int :  
        return db.query(self.model).count()
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)

        db_obj = self.model(**obj_in_data)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail="Data integrity issue.")

    def get_by_field(
        self, db: Session, *, field_name: str, field_value: str
    ) -> ModelType:
        return (
            db.query(self.model)
            .filter(getattr(self.model, field_name) == field_value)
            .first()
        )

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
        except IntegrityError as e:
            e.add_detail("An error occured while trying to update " + str(e.params))
            raise e
        return db_obj

    def remove(self, db: Session, *, id: any) -> ModelType:
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj

    def get_paginated(self, db: Session, *, skip: int = 0, limit: int = 10) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def get_paginated_with_filter(
        self, db: Session, *, filter_conditions: Dict[str, Any], skip: int = 0, limit: int = 10
    ) -> List[ModelType]:
        query = db.query(self.model)
        for field, value in filter_conditions.items():
            query = query.filter(getattr(self.model, field) == value)
        return query.offset(skip).limit(limit).all()
