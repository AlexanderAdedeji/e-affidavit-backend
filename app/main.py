from fastapi import Depends, FastAPI, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn
from app.core.settings.configurations import settings
import starlette.responses as _responses
from starlette.middleware import Middleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.database.sessions.session import engine
from app.database.base import Base
from app.database.sessions.mongo_client import db_client, client
from app.api.routes.routes import router as global_router


Base.metadata.create_all(engine)
# CORS configuration
origins = ["*"]  # Replace with your allowed origins
methods = ["GET", "POST", "PUT", "DELETE"]  # Specify allowed methods

# Security middleware (example)
security_middleware = Middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=methods,
    allow_headers=["*"],
    expose_headers=["*"],
)


def create_application_instance() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME, middleware=[security_middleware])
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.info(f"Request: {request.method} {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": f"HTTP error occurred: {exc.detail}"},
        )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.info(f"Request: {request.method} {request.url}")
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"An unexpected error occurred: {str(exc)}"},
        )

    # Your existing middleware and route includes go here
    app.include_router(global_router, prefix=settings.API_URL_PREFIX)

    return app




app = create_application_instance()


@app.get("/")
async def root():
    return _responses.RedirectResponse("/docs")


@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = client

    app.mongodb = app.mongodb_client.get_database("E-affidavit-dev")
    print("Hello world")


@app.on_event("shutdown")
async def shutdown_db_client():
    print("bye world")
    app.mongodb_client.close()


if __name__=="__main__":
    uvicorn.run("app.main:app",host="0.0.0.0",port=4100,reload=True)