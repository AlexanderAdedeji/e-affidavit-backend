from typing import Type, TypeVar, Generic, Optional
from pydantic.generics import GenericModel


T = TypeVar("T")


# Generic response model that can be used with any data type
class GenericResponse(GenericModel, Generic[T]):
    message: str
    status_code: int
    data: Optional[T]




def create_response(
   message: str = "", status_code: int = "Success", data: Optional[T] = None
) -> GenericResponse[T]:
    return GenericResponse[T](message=message, status_code=status_code, data=data)



