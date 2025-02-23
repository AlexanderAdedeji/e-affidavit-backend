import json
from typing import Any, Dict, List, Union

from fastapi import BackgroundTasks, Depends
from loguru import logger
from postmarker.core import PostmarkClient
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_db
from app.core.settings.configurations import settings
from app.models.email_model import Email
from app.repositories.email_repo import email_repo
from app.schemas.email_schema import EmailCreate, EmailUpdate

# class EmailService:
#     def __init__(self):
#         self.client = PostmarkClient(server_token=settings.POSTMARK_API_TOKEN)
#         logger.info("EmailService initialized with Postmark client.")

#     def send_email_with_template(
#         self,
#         template_id: int,
#         db: Session,
#         template_dict: Dict[str, Any],
#         recipient: Union[List[EmailStr], EmailStr],
#         background_tasks: BackgroundTasks,
#     ):
#         email = email_repo.create(
#             db=db,
#             obj_in=EmailCreate(
#                 template_id=template_id,
#                 template_dict=json.dumps(template_dict),
#                 recipient=recipient,
#                 sender=settings.DEFAULT_EMAIL_SENDER,
#             ),
#         )

#         background_tasks.add_task(
#             self._send_email_with_template,
#             db=db,
#             email=email,
#             template_dict=template_dict,
#         )


#     async def _send_email_with_template(
#         self, db: Session, email: Email, template_dict: Dict[str, Any]
#     ):
#         session = get_db()  # Create a new session for the background task
#         try:
#             response = self.client.emails.send_with_template(
#                 TemplateId=email.template_id,
#                 TemplateModel=template_dict,
#                 From=settings.DEFAULT_EMAIL_SENDER,
#                 To=email.recipient,
#             )
#             if response["ErrorCode"] == 0:
#                 email_repo.mark_as_delivered(session, db_obj=email)
#                 logger.info(f"Email to {email.recipient} marked as delivered.")
#             else:
#                 logger.error(f"Failed to send email: {response['Message']}")
#                 email_repo.update(
#                     db_obj=email,
#                     obj_in=EmailUpdate(delivered=False, extra_data=response["Message"]),
#                     db=session,
#                 )
#         except Exception as e:
#             logger.error(f"Exception occurred while sending email: {str(e)}")
#             email_repo.update(
#                 db_obj=email,
#                 obj_in=EmailUpdate(delivered=False, extra_data=str(e)),
#                 db=session,
#             )
#         finally:
#             session.close()
class EmailService:
    def __init__(self):
        self.client = PostmarkClient(server_token=settings.POSTMARK_API_TOKEN)
        logger.info("EmailService initialized with Postmark client.")

    def send_email_with_template(
        self,
        template_id: int,
        db: Session,
        template_dict: Dict[str, Any],
        recipient: Union[List[EmailStr], EmailStr],
        background_tasks: BackgroundTasks,
    ):
        if not recipient:
            raise ValueError("Recipient email address is required.")
        if not template_dict:
            raise ValueError("Template data is required.")

        To = recipient if isinstance(recipient, str) else ", ".join(recipient)

        email = email_repo.create(
            db=db,
            obj_in=EmailCreate(
                template_id=template_id,
                template_dict=template_dict,
                recipient=To,
                sender=settings.DEFAULT_EMAIL_SENDER,
            ),
        )

        background_tasks.add_task(
            self._send_email_with_template,
            db=db,
            email=email,
            template_dict=template_dict,
        )

    async def _send_email_with_template(
        self, db: Session, email: Email, template_dict: Dict[str, Any]
    ):
        session = get_db()  # Create a new session for background tasks
        try:
            response = self.client.emails.send_with_template(
                TemplateId=email.template_id,
                TemplateModel=template_dict,
                From=settings.DEFAULT_EMAIL_SENDER,
                To=email.recipient,
            )
            if not response or "ErrorCode" not in response:
                raise ValueError("Invalid response from Postmark API.")

            if response["ErrorCode"] == 0:
                email_repo.mark_as_delivered(session, db_obj=email)
                logger.info(f"Email to {email.recipient} marked as delivered.")
            else:
                logger.error(f"Failed to send email: {response['Message']}")
                email_repo.update(
                    db_obj=email,
                    obj_in=EmailUpdate(delivered=False, extra_data=response["Message"]),
                )
        except Exception as e:
            logger.error(f"Exception occurred while sending email: {str(e)}")
            email_repo.update(
                db=session,
                db_obj=email,
                obj_in=EmailUpdate(delivered=False, extra_data=str(e)),
            )
        finally:
            session.close()


email_service = EmailService()
