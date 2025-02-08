# app/api/routes/log_routes.py
import os
from typing import List

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.core.settings.logs.mongo_log_sink import log_collection

router = APIRouter()


@router.get("/logs/{request_id}", summary="Retrieve logs by request ID")
async def get_logs_by_request_id(request_id: str):
    """
    Retrieves all logs associated with a given request ID.
    The request ID should be set in the extra context of your log messages.
    """
    # Query for logs that have extra.request_id equal to the provided request_id.
    logs_cursor = log_collection.find({"extra.request_id": request_id})
    logs: List[dict] = list(logs_cursor)
    if not logs:
        raise HTTPException(
            status_code=404, detail="No logs found for the given request ID."
        )

    # Convert ObjectId to string
    for log in logs:
        log["_id"] = str(log["_id"])
    return JSONResponse(content=logs)
