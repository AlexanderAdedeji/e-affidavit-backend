from fastapi import Depends, FastAPI, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware
from app.core.settings.handler import logger
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

# Initialize database schema
Base.metadata.create_all(engine)


# CORS configuration
origins = settings.ALLOWED_ORIGINS.split(",")
methods = settings.ALLOWED_METHODS.split(",")



security_middleware = Middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def create_application_instance() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME, middleware=[security_middleware])

    # Exception Handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP exception: {request.method} {request.url} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": f"{exc.detail}"},
        )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Outgoing response: {response.status_code} for {request.method} {request.url}")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.warning(f"Validation error: {request.method} {request.url} - {exc.errors()}")
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {str(exc)} - Request: {request.method} {request.url}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"An unexpected error occurred: {str(exc)}"},
        )
    app.include_router(global_router, prefix=settings.API_URL_PREFIX)

    return app


app = create_application_instance()


@app.get("/")
async def root():
    """Redirect to API documentation."""
    return _responses.RedirectResponse("/docs")




@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = client
    app.mongodb = app.mongodb_client.get_database(settings.MONGO_DB_NAME)
    logger.info("MongoDB client started successfully")
    


@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Shutting down mongoDB client...")
    app.mongodb_client.close()
    logger.info("MongoDB client shutdown complete")


# if __name__=="__main__":
#     uvicorn.run("main:app",host="0.0.0.0",port=7000,reload=True)
