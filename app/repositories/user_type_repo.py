from app.models.user_type_model import UserType
from sqlalchemy.orm import Session
from commonLib.repositories.relational_repository import Base


class UserTypeRepositories(Base[UserType]):
    def get_by_name(self, db: Session, *, name:str) -> UserType:
        return db.query(UserType).filter(UserType.name == name).first()
    


user_type_repo = UserTypeRepositories(UserType)
