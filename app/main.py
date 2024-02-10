from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware
from loguru import logger
import starlette.responses as _responses
from starlette.middleware import Middleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException



# CORS configuration
origins = ["https://example.com"]  # Replace with your allowed origins
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
    app = FastAPI(title="E-Affidavit",middleware=[security_middleware])

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


    return app


app = create_application_instance()



@app.get("/")
async def root():
    return _responses.RedirectResponse("/docs")
