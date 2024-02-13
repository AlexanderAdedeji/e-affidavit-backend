from fastapi import APIRouter

from app.api.routes import (
    user_routes,
    user_type_routes,
    court_system_routes,
    commissioner_routes,
    admin_routes
)


router = APIRouter()


router.include_router(user_routes.router, tags=["Users"], prefix="/users")
router.include_router(
    user_type_routes.router, tags=["Users Type"], prefix="/users_type"
)
router.include_router(
    court_system_routes.router, tags=["Court System"], prefix="/users_type"
)
router.include_router(
    commissioner_routes.router, tags=["Commissioner"], prefix="/commissioner"
)

router.include_router(
    admin_routes.router, tags=["Admin"], prefix="/admin"
)

