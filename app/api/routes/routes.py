from fastapi import APIRouter

from app.api.routes import (
    authentication_routes,
    user_routes,
    user_type_routes,
    court_system_routes,
    commissioner_routes,
    admin_routes,
    affidavit_routes,
    head_of_unit_routes
)


router = APIRouter()

router.include_router(authentication_routes.router, tags=["Authentication"], prefix="/authentication")
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


router.include_router(
    affidavit_routes.router, tags=["Affidavits"], prefix="/affidavit"
)



router.include_router(
    head_of_unit_routes.router, tags=["Head Of Unit"], prefix="/head_of_unit"
)
