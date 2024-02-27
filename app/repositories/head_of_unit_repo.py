from uuid import uuid4
from app.models.commissioner_profile_model import CommissionerProfile
from sqlalchemy.orm import Session
from app.models.head_of_unit_model import HeadOfUnit
from app.schemas.user_schema import CommissionerProfileBase, HeadOfUnitBase, HeadOfUnitCreate

from commonLib.repositories.relational_repository import Base


class HeadOfUnitRepositories(Base[HeadOfUnit]):
    def create(self, db, *, obj_in: HeadOfUnitBase):
        db_obj = HeadOfUnit(
            head_of_unit_id=obj_in.head_of_unit_id,

            jurisdiction_id = obj_in.jurisdiction_id,
            created_by_id = obj_in.created_by_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


head_of_unit_repo = HeadOfUnitRepositories(HeadOfUnit)
