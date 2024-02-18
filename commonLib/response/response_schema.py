from typing import Type, TypeVar, Generic, Optional
from pydantic.generics import GenericModel
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from starlette.status import HTTP_200_OK

T = TypeVar("T")


# Generic response model that can be used with any data type
class GenericResponse(GenericModel, Generic[T]):
    message: str
    status_code: int
    data: Optional[T]


# Dependency to dynamically create a response model based on the endpoint's return type
# def create_reponse(data_model: Type[BaseModel]):
#     def wrapper():
#         return lambda message="", status="Success", data=None: GenericResponse[data_model](
#             message=message, status=status, data=data
#         )
#     return wrapper


def create_response(
   message: str = "", status_code: int = "Success", data: Optional[T] = None
) -> GenericResponse[T]:
    return GenericResponse[T](message=message, status_code=status_code, data=data)


# response: GenericResponse[List[UserWithToken]] = Depends(response_model(List[UserWithToken])),
