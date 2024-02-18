from fastapi import APIRouter

# Importing routes
from app.api.routes import (
    authentication_routes,
    user_routes,
    user_type_routes,
    court_system_routes,
    commissioner_routes,
    admin_routes,
    affidavit_routes,
    head_of_unit_routes,
    reports_routes
)

# Creating a main router instance
router = APIRouter()

# Including authentication-related routes
router.include_router(authentication_routes.router, tags=["Authentication"], prefix="/auth")

# Routes for managing user types or roles
router.include_router(user_type_routes.router, tags=["User Types"], prefix="/user_types")

# Routes for court system-related operations
router.include_router(court_system_routes.router, tags=["Court System"], prefix="/court_system")


# Routes for managing user entities
router.include_router(user_routes.router, tags=["Users"], prefix="/users")




# Routes specific to commissioner operations
router.include_router(commissioner_routes.router, tags=["Commissioners"], prefix="/commissioners")

# Administrative routes for managing the application
router.include_router(admin_routes.router, tags=["Admin"], prefix="/admin")

# Routes for managing affidavits
router.include_router(affidavit_routes.router, tags=["Affidavits"], prefix="/affidavits")

# Routes for operations related to the head of unit
router.include_router(head_of_unit_routes.router, tags=["Head of Unit"], prefix="/head_of_unit")

# Routes for operations related to the reports
router.include_router(reports_routes.router, tags=["Reports"], prefix="/report")
