from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from loguru import logger
from pydantic import ValidationError

from app.core.errors import error_strings
from app.core.errors.exceptions import InvalidTokenException
from app.core.settings.configurations import settings
from app.schemas.jwt_schema import JWTInvite, JWTUser

# from app.schemas.jwt_schema import JWTOrganisation

JWT_ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.SECRET_KEY
JWT_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES


class JWTService:
    def __init__(
        self,
        secret_key: str = settings.SECRET_KEY,
        algorithm: str = settings.JWT_ALGORITHM,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = settings.JWT_EXPIRE_MINUTES

    def decode_token(self, token: str):
        try:
            decoded_payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            logger.error(decoded_payload['exp'])
            exp_timestamp = decoded_payload.get("exp")
            if exp_timestamp is None:
                raise InvalidTokenException(detail="Token missing expiration claim.")
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
            if exp_datetime < datetime.now(timezone.utc):
                raise InvalidTokenException(detail="Token has expired.")
            return decoded_payload
        except jwt.PyJWTError as decode_error:
            logger.error(f"JWT decode error: {decode_error}")
            raise InvalidTokenException(
                detail="Unable to decode JWT token"
            ) from decode_error
        except KeyError as decode_error:
            logger.error(f"Key error while decoding JWT: {decode_error}")
            raise InvalidTokenException(
                detail="Malformed payload in token"
            ) from decode_error
        except ValidationError as validation_error:
            logger.error(f"Validation error in token: {validation_error}")
            raise InvalidTokenException(
                detail="Malformed payload in token"
            ) from validation_error

    def generate_token(self, payload: dict, expires_delta: timedelta = None):
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.expire_minutes)

        now = datetime.now(timezone.utc)
        expires_at = now + expires_delta

        payload.update({"exp": expires_at.timestamp(), "iat": now.timestamp()})
        logger.debug({"jwt_content": payload})
        encoded_token = jwt.encode(
            payload=payload, key=str(self.secret_key), algorithm=self.algorithm
        )
        return encoded_token

    def get_user_id_from_token(self, token: str):
        decoded_payload = self.decode_token(token)
        return {"id": decoded_payload["id"]}

    def get_all_details_from_token(self, token: str):
        return self.decode_token(token)

    def get_user_email_from_token(self, token: str):
        decoded_payload = self.decode_token(token)
        return decoded_payload["email"]

    def generate_invitation_token(self, id, expires_delta: timedelta = None):
        jwt_content = JWTInvite(id=id).dict()
        if expires_delta is None:
            expires_delta = timedelta(minutes=JWT_EXPIRE_MINUTES)

        now = datetime.now(timezone.utc)
        expires_at = now + expires_delta

        jwt_content.update({
            "iat": now.timestamp(),
            "exp": expires_at.timestamp(),
            "nbf": now.timestamp(),
        })
        logger.debug({"jwt_content": jwt_content})
        encoded_token = jwt.encode(
            payload=jwt_content, key=str(SECRET_KEY), algorithm=JWT_ALGORITHM
        )
        return encoded_token


jwt_service = JWTService()
