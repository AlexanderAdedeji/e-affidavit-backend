

from sqlalchemy.orm import Session

from app.models.affidavit_models import AffidavitCategory
from commonLib.repositories.relational_repository import Base


class CategoryRepositories(Base[AffidavitCategory]):
    def get_by_name(self,db:Session, *, name: str):
        """Get category by its name"""
        pattern =f"%{name}%"
        return db.query(AffidavitCategory).filter(AffidavitCategory.name.like(name)).first()
    


category_repo =  CategoryRepositories(AffidavitCategory)