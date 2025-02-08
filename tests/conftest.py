# tests/conftest.py
import asyncio
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings.configurations import settings
from app.main import app  # your FastAPI app instance
from commonLib.models.base_class import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a test database and tables
@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()



@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

# For async integration tests using httpx
@pytest.fixture(scope="session")
async def async_client():
    async with AsyncClient(app=app, base_url="mongodb+srv://alexadedeji15:YvwZ9RmXcUsDblDd@e-affidavittest.lagiwwp.mongodb.net/?retryWrites=true&w=majority") as ac:
        yield ac
