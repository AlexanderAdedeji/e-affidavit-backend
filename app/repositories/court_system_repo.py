from app.models.court_system_models import Court, Jurisdiction, State
from commonLib.repositories.relational_repository import Base, ModelType



class CourtSystemRepositories(Base[ModelType]):
    
    pass

state_repo = CourtSystemRepositories[State](State)
court_repo = CourtSystemRepositories[Court](Court)
jurisdiction_repo = CourtSystemRepositories[Jurisdiction](Jurisdiction)

