from fastapi import APIRouter
import logging

# Importing all necessary routes
from app.api.routes import (
    authentication_routes,
    user_routes,
    user_type_routes,
    court_system_routes,
    commissioner_routes,
    admin_routes,
    # affidavit_routes,
    head_of_unit_routes,
    reports_routes,
)

# Set up logger for detailed route inclusion
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Creating a main router instance
router = APIRouter()

# Including authentication-related routes
logger.info("Including authentication-related routes")
router.include_router(
    authentication_routes.router, 
    tags=["Authentication"], 
    prefix="/auth",
    responses={404: {"description": "Not found"}}
)

# Routes for managing user types or roles
logger.info("Including user type management routes")
router.include_router(
    user_type_routes.router, 
    tags=["User Types"], 
    prefix="/user_types",
    responses={404: {"description": "Not found"}}
)

# Routes for court system-related operations
logger.info("Including court system routes")
router.include_router(
    court_system_routes.router, 
    tags=["Court System"], 
    prefix="/court_system",
    responses={404: {"description": "Not found"}}
)

# Routes for managing user entities
logger.info("Including user management routes")
router.include_router(
    user_routes.router, 
    tags=["Users"], 
    prefix="/users",
    responses={404: {"description": "Not found"}}
)

# Routes specific to commissioner operations
logger.info("Including commissioner-specific routes")
router.include_router(
    commissioner_routes.router, 
    tags=["Commissioners"], 
    prefix="/commissioners",
    responses={404: {"description": "Not found"}}
)

# Administrative routes for managing the application
logger.info("Including administrative routes")
router.include_router(
    admin_routes.router, 
    tags=["Admin"], 
    prefix="/admin",
    responses={404: {"description": "Not found"}}
)

# Routes for operations related to affidavits
# logger.info("Including affidavit routes")
# router.include_router(
#     affidavit_routes.router, 
#     tags=["Affidavits"], 
#     prefix="/affidavits",
#     responses={404: {"description": "Not found"}}
# )

# Routes for operations related to the head of unit
logger.info("Including head of unit routes")
router.include_router(
    head_of_unit_routes.router, 
    tags=["Head of Unit"], 
    prefix="/head_of_unit",
    responses={404: {"description": "Not found"}}
)

# Routes for operations related to the reports
logger.info("Including report routes")
router.include_router(
    reports_routes.router, 
    tags=["Reports"], 
    prefix="/reports",
    responses={404: {"description": "Not found"}}
)
