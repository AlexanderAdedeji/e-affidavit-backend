from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo


router = APIRouter()
