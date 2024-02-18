import json
from typing import Any, Dict, List, Union

from fastapi import Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_db
from app.core.settings.configurations import settings
from app.models.email_model import Email
from app.schemas.email_schema import EmailCreate, EmailUpdate
from app.repositories.email_repo import EmailRepository
from loguru import logger
from postmarker.core import PostmarkClient
from pydantic import EmailStr



class EmailService:
    def __init__(self, db: Session):
        self.db = db
        self.email_repo = EmailRepository(db)
        self.client = PostmarkClient(server_token=settings.POSTMARK_API_TOKEN)
        logger.info("email")


    async def send_email_with_template(
        self,
        template_id: int,
        template_dict: Dict[str, Any],
        recipient: Union[List[EmailStr], EmailStr],
        background_tasks: BackgroundTasks,
    ):
        email = self.email_repo.create(
            obj_in=EmailCreate(
                template_id=template_id,
                template_dict=json.dumps(template_dict),
                recipient=recipient,
                sender=settings.DEFAULT_EMAIL_SENDER,
            )
        )
        
        background_tasks.add_task(
            self._send_email_with_template, email=email, template_dict=template_dict
        )

    async def _send_email_with_template(
        self, email: Email, template_dict: Dict[str, Any]
    ):
        try:
            response = self.client.emails.send_with_template(
                TemplateId=email.template_id,
                TemplateModel=template_dict,
                From=settings.DEFAULT_EMAIL_SENDER,
                To=email.recipient,
            )
            if response["ErrorCode"] == 0:
                self.email_repo.mark_as_delivered(email=email)
            else:
                self.email_repo.update(
                    db_obj=email,
                    obj_in=EmailUpdate(delivered=False, extra_data=response["Message"]),
                )
        except Exception as e:
            logger.error(e)
            self.email_repo.update(
                db_obj=email,
                obj_in=EmailUpdate(delivered=False, extra_data=str(e)),
            )


email_service = EmailService(db=Depends(get_db))
