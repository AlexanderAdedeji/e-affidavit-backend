from typing import Type, TypeVar, Generic, Optional, Dict, Any
from pydantic.generics import GenericModel


T = TypeVar("T")


class GenericResponse(GenericModel, Generic[T]):
    message: str
    status_code: int
    data: Optional[T]
    metadata: Optional[Dict[str, Any]] = None


def create_response(
    message: str = "",
    status_code: int = 200,
    data: Optional[T] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> GenericResponse[T]:
    return GenericResponse[T](message=message, status_code=status_code, data=data, metadata=metadata)
