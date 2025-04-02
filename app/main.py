import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.routes.routes import router as global_router
from app.core.settings.configurations import settings
from app.core.settings.logs.handler import logger  
from app.database.base import Base
from app.database.sessions.mongo_client import client
from app.database.sessions.session import engine
from app.middleware.request_id import RequestIDMiddleware  # New middleware for request IDs

# Create database schema (for SQLAlchemy)
Base.metadata.create_all(engine)


def create_application_instance() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)

    # Add middlewares
    app.add_middleware(RequestIDMiddleware)  # Binds a request ID to each request
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Global Exception Handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP exception: {request.method} {request.url} - {exc.detail}")
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.warning(
            f"Validation error: {request.method} {request.url} - {exc.errors()}"
        )
        detail = [
        {
            "loc": error.get("loc", []),
            "msg": str(error.get("msg", "")),
            "type": error.get("type", "")
        }
        for error in exc.errors()
    ]
        return JSONResponse(status_code=422, content={"detail": detail})
  

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled error: {exc} - Request: {request.method} {request.url}"
        )
        return JSONResponse(
            status_code=500, content={"detail": f"An unexpected error occurred: {exc}"}
        )

   
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
    
        logger.info(f"Incoming request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(
            f"Outgoing response: {response.status_code} for {request.method} {request.url}"
        )
        return response

    # Include API routes under the configured prefix
    app.include_router(global_router, prefix=settings.API_URL_PREFIX)

    return app


# Create the application instance
app = create_application_instance()


@app.get("/")
async def root():
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


# MongoDB startup and shutdown events
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = client
    app.mongodb = app.mongodb_client.get_database(settings.MONGO_DB_NAME)
    logger.info("MongoDB client started successfully")


@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Shutting down MongoDB client...")
    app.mongodb_client.close()
    logger.info("MongoDB client shutdown complete")


# Uncomment the following for local development:
# if __name__ == "__main__":
#     uvicorn.run("app.main:app", host="0.0.0.0", port=7000, reload=True)
