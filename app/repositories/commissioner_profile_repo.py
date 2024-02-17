from uuid import uuid4
from app.models.commissioner_profile_model import CommissionerProfile
from sqlalchemy.orm import Session
from app.schemas.user_schema import CommissionerProfileBase

from commonLib.repositories.relational_repository import Base, ModelType


class CommissionerRepositiories(Base[CommissionerProfile]):
    def create(self, db, *, obj_in: CommissionerProfileBase):
        db_obj = CommissionerProfile(id=uuid4().hex, **obj_in)
        db_obj.set_password(obj_in.password)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    pass



comm_profile_repo = CommissionerRepositiories(CommissionerProfile)