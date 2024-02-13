from typing import Any, Dict, List, Optional, Union

from app.models.email_model import Email
from commonLib.repositories.relational_repository import Base
from sqlalchemy.orm import Session


class EmailRepository(Base[Email]):
    def mark_as_delivered(self, db: Session, *, db_obj: Email) -> Email:
        return super().update(db, db_obj=db_obj, obj_in={"delivered": True})


email_repo = EmailRepository(Email)
