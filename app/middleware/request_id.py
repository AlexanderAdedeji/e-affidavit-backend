
import uuid

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        # Bind request-level context for logging. Additional fields (like user_id) can be updated later.
        with logger.contextualize(request_id=request_id, user_id="N/A"):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
