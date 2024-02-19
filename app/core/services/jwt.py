import jwt
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from loguru import logger
from pydantic import ValidationError
from app.core.errors.exceptions import InvalidTokenException
from app.core.settings.configurations import settings
from app.core.errors import error_strings
from app.schemas.jwt_schema import JWTInvite, JWTUser
# from app.schemas.jwt_schema import JWTOrganisation

JWT_ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.SECRET_KEY
JWT_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES


def decode_token(token: str):
    try:
        decode_payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if decode_payload["exp"] <= datetime.now().timestamp():
            raise InvalidTokenException(detail="token has expired.")
        return decode_payload
    except jwt.PyJWTError as decode_error:
        raise ValueError("unable to decode JWT token") from decode_error
    except KeyError as decode_error:
        raise ValueError("unable to decode JWT token") from decode_error
    except ValidationError as validation_error:
        raise ValueError("malformed payload in token") from validation_error


def get_user_id_from_token(token: str):
    decode_payload = decode_token(token)
    return {"id": decode_payload["id"]}


def get_all_details_from_token(token: str):
    decode_payload = decode_token(token)
    return decode_payload


def get_user_email_from_token(token: str):
    decode_payload = decode_token(token)
    return decode_payload["email"]

def generate_invitation_token(id, expires_delta: timedelta = None):
        jwt_content = JWTInvite(id=id).dict()
        if expires_delta is None:
            expires_delta = timedelta(minutes=JWT_EXPIRE_MINUTES)

        now = datetime.now()
        expires_at = now + expires_delta

        jwt_content["exp"] = expires_at.timestamp()
        jwt_content["iat"] = now.timestamp()
        logger.debug({"jwt_content":jwt_content})
        encoded_token = jwt.encode(
            payload=jwt_content, key=str(SECRET_KEY), algorithm=JWT_ALGORITHM
        )
        return encoded_token

