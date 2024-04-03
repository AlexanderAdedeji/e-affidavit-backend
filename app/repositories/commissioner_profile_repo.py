from uuid import uuid4
from app.models.commissioner_profile_model import CommissionerProfile
from sqlalchemy.orm import Session
from app.schemas.user_schema import CommissionerAttestation, CommissionerProfileBase

from commonLib.repositories.relational_repository import Base, ModelType


class CommissionerRepositiories(Base[CommissionerProfile]):
    def create(self, db, *, obj_in: CommissionerProfileBase):
        db_obj = CommissionerProfile(
            commissioner_id=obj_in.commissioner_id,
            court_id=obj_in.court_id,
            created_by_id=obj_in.created_by_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_profile_by_commissioner_id(self, db, *, commissioner_id: str):
        return (
            db.query(CommissionerProfile)
            .filter(CommissionerProfile.commissioner_id == commissioner_id)
            .first()
        )

    def updateAttestation(
        self, db, *, attestation_obj: CommissionerAttestation, db_obj
    ):
        return super().update(db, db_obj=db_obj, obj_in=attestation_obj)


comm_profile_repo = CommissionerRepositiories(CommissionerProfile)
