


from app.models.user_invite_models import UserInvite
from app.schemas.user_schema import CreateInvite
from commonLib.repositories.relational_repository import Base


class UserInviteRepositories(Base[UserInvite]):
    pass


user_invite_repo = UserInviteRepositories(UserInvite)
