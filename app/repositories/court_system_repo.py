from typing import Type
from sqlalchemy.orm import Session
from app.models.court_system_models import Court, Jurisdiction, State
from commonLib.repositories.relational_repository import Base, ModelType



class CourtSystemRepositories(Base[ModelType]):
    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model
    def get_by_name(self, db: Session, *, name):
        return db.query(self.model).filter(self.model.name == name).first()
    pass

state_repo = CourtSystemRepositories[State](State)
court_repo = CourtSystemRepositories[Court](Court)
jurisdiction_repo = CourtSystemRepositories[Jurisdiction](Jurisdiction)

