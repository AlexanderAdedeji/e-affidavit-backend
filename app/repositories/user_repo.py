from uuid import uuid4
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from commonLib.repositories.relational_repository import Base
from app.models.user_model import User
from app.core.settings.security import security
from app.schemas.user_schema import UserCreate
from app.core.settings.security import security


class UserRepositories(Base[User]):
    def get_by_email(self, db: Session, *, email):
        user = db.query(User).filter(User.email == email).first()
        return user

    def create(self, db, *, obj_in: UserCreate):
        user_obj = User(
            id=uuid4().hex,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            email=obj_in.email,
            hashed_password=security.get_password_hash(obj_in.password),
        )
        db.add(user_obj)
        db.commit()
        db.refresh(user_obj)
        return user_obj


user_repo = UserRepositories(User)
