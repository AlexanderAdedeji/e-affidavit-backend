from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user_invite_models import UserInvite
from app.schemas.user_schema import CreateInvite
from commonLib.repositories.relational_repository import Base


class UserInviteRepositories(Base[UserInvite]):

    # def get_user_invite_info(self, db: Session, *, invite_id: str):
    #     return db.query(UserInvite).filter(UserInvite.id == invite_id).first()

    def mark_invite_as_accepted( self, db: Session, *, db_obj: UserInvite):
        if db_obj.is_accepted:
            return db_obj
        return super().update(db, db_obj=db_obj, obj_in={"is_accepted": True, "accepted_at":datetime.datetime.now()})

user_invite_repo = UserInviteRepositories(UserInvite)
