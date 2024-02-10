from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, ValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK

T = TypeVar('T', bound=BaseModel)

class GenericResponse(Generic[T], JSONResponse):
    def __init__(self, data: Optional[T] = None, message: str = "", status_code: int = HTTP_200_OK):
        try:
            content = {
                "message": message,
                "data": data.dict() if data else None
            }
        except ValidationError as e:
            content = {"message": "Data validation error", "errors": e.errors()}
            status_code = 422
        super().__init__(content=content, status_code=status_code)
