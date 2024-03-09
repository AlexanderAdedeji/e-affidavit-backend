from typing import List
from uuid import uuid4
from app.models.commissioner_profile_model import CommissionerProfile
from sqlalchemy.orm import Session
from app.models.court_system_models import Court
from app.models.head_of_unit_model import HeadOfUnit
from app.schemas.user_schema import  HeadOfUnitBase, HeadOfUnitCreate

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

    def get_commissioners_under_jurisdiction(self, db: Session, jurisdiction_id: str) -> List[CommissionerProfile]:
        court_ids = db.query(Court.id).filter(Court.jurisdiction_id == jurisdiction_id).all()
        court_ids = [court_id[0] for court_id in court_ids]  # Extract court IDs from the result
        commissioner_profiles = db.query(CommissionerProfile).filter(CommissionerProfile.court_id.in_(court_ids)).all()

        return commissioner_profiles
    def get_courts_under_jurisdiction(self, db: Session, jurisdiction_id: str) -> List[CommissionerProfile]:
        courts = db.query(Court).filter(Court.jurisdiction_id == jurisdiction_id).all()
        return courts
head_of_unit_repo = HeadOfUnitRepositories(HeadOfUnit)
