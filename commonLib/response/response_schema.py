from typing import Any, Dict, Generic, Optional, TypeVar
from app.schemas.pagination_schema import PaginationMeta
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
    pagination: Optional[PaginationMeta] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> GenericResponse[T]:
    meta: Dict[str, Any] = extra_metadata.copy() if extra_metadata else {}
    if pagination:
        meta["pagination"] = pagination
    return GenericResponse[T](
        message=message,
        status_code=status_code,
        data=data,
        metadata=meta if meta else None,
    )
