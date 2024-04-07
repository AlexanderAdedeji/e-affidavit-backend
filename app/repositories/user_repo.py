from uuid import uuid4
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.models.user_invite_models import UserInvite
from commonLib.repositories.relational_repository import Base
from app.models.user_model import User
from app.core.settings.security import security
from app.schemas.user_schema import UserCreate
from app.core.settings.security import security


class UserRepositories(Base[User]):
    def get_by_email(self, db: Session, *, email):
        return db.query(User).filter(User.email == email).first()

    def create(self, db, *, obj_in: UserCreate):
        db_obj = User(
            id=uuid4().hex,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            email=obj_in.email,
            user_type_id=obj_in.user_type_id,
            is_active=True
        )
        db_obj.set_password(obj_in.password)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_verification_token(self, db: Session, *, email):
        user = db.query(User).filter(User.email == email).first()
        return user.generate_verification_token()

    def activate(self, db: Session, *, db_obj: User) -> User:
        return self._set_activation_status(db=db, db_obj=db_obj, status=True)

    def deactivate(self, db: Session, *, db_obj: User) -> User:
        return self._set_activation_status(db=db, db_obj=db_obj, status=False)

    def _set_activation_status(
        self, db: Session, *, db_obj: User, status: bool
    ) -> User:
        if db_obj.is_active == status:
            return db_obj
        return super().update(db, db_obj=db_obj, obj_in={"is_active": status})


    def get_users_by_user_type(self, db: Session, *, user_type_id: str) -> List[User]:
        return db.query(User).filter(User.user_type_id == user_type_id).all()

    def update_password(self, db: Session,db_obj:User, password: str) -> User:
        user = user_repo.update(
            db=db,
            db_obj=db_obj,
            obj_in={"hashed_password": security.get_password_hash(password)},
        )
        return user
user_repo = UserRepositories(User)
