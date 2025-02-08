"""
Main router aggregation for the API.

This module includes all sub-routers (authentication, user management, admin, etc.) into a single FastAPI router.
"""



from fastapi import APIRouter
from app.core.settings.logs.handler import logger
from app.api.routes import (
    authentication_routes,
    user_routes,
    user_type_routes,
    court_system_routes,
    commissioner_routes,
    admin_routes,
    head_of_unit_routes,
    reports_routes,
)

# Create the main API router instance.
router = APIRouter()

# Define a list of tuples with (router_instance, prefix, tag)
subrouters = [
    (authentication_routes.router, "/auth", "Authentication"),
    (user_type_routes.router, "/user_types", "User Types"),
    (court_system_routes.router, "/court_system", "Court System"),
    (user_routes.router, "/users", "Users"),
    (commissioner_routes.router, "/commissioners", "Commissioners"),
    (admin_routes.router, "/admin", "Admin"),
    (head_of_unit_routes.router, "/head_of_unit", "Head of Unit"),
    (reports_routes.router, "/reports", "Reports"),
]

# Loop through the list and include each subrouter.
for subrouter, prefix, tag in subrouters:
    logger.info(f"Including {tag} routes with prefix '{prefix}'")
    router.include_router(
        subrouter,
        prefix=prefix,
        tags=[tag],
        responses={404: {"description": "Not found"}},
    )
