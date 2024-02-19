from uuid import uuid4
from app.models.commissioner_profile_model import CommissionerProfile
from sqlalchemy.orm import Session
from app.models.head_of_unit_model import HeadOfUnit
from app.schemas.user_schema import CommissionerProfileBase, HeadOfUnitCreate

from commonLib.repositories.relational_repository import Base


class HeadOfUnitRepositories(Base[HeadOfUnit]):
    def create(self, db, *, obj_in: HeadOfUnitCreate):
        db_obj = HeadOfUnit(id=uuid4().hex, **obj_in)
        db_obj.set_password(obj_in.password)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


head_of_unit_repo = HeadOfUnitRepositories(HeadOfUnit)
