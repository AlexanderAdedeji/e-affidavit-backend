from app.models.user_type_model import UserType
from commonLib.repositories.relational_repository import Base


class UserTypeRepositories(Base[UserType]):
    pass


user_type_repo = UserTypeRepositories(UserType)
