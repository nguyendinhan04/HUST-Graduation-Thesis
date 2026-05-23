from .jobs import router as jobs_router
from .matching import router as matching_router
from .recommendations import router as recommendations_router
from .users import router as users_router
from .auth import router as auth_router

__all__ = [
    "jobs_router",
    "matching_router",
    "recommendations_router",
    "users_router",
    "auth_router",
]
