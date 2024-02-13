# from typing import Generic, TypeVar, Optional, Dict
# from pydantic import BaseModel, ValidationError
# from fastapi.responses import JSONResponse
# from starlette.status import HTTP_200_OK

# T = TypeVar ("T",BaseModel)


# class BaseResponseModel(BaseModel):
#     status_code: int
#     message: str


# class ResponseModel(Generic[T], BaseResponseModel):
#     data: Optional[T]

# # 
# class GenericResponse(Generic[T], BaseModel):
#     def __init__(self, ResponseModel):
#         try:
#             content = {"message": ResponseModel.message, "data": ResponseModel.data.dict() if ResponseModel.data else None}
#         except ValidationError as e:
#             content = {"message": "Data validation error", "errors": e.errors()}
#             status_code = 422
#         super().__init__(content=content, status_code=status_code)


# def create_response(
#     data: Optional[BaseModel] = None, message: str = "", status_code: int = HTTP_200_OK
# ) -> GenericResponse:
#     return GenericResponse(data=data, message=message, status_code=status_code)


from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, ValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK

T = TypeVar("T", bound=BaseModel)

class BaseResponseModel(BaseModel):
    status_code: int
    message: str

class ResponseModel(Generic[T], BaseResponseModel):
    data: Optional[T]





    data: Optional[T] = None

def create_response(data: Optional[BaseModel] = None, message: str = "", status_code: int = HTTP_200_OK) -> JSONResponse:
    response_model = BaseResponseModel(status_code=status_code, message=message, data=data)
    return JSONResponse(content=response_model.dict(), status_code=status_code)
