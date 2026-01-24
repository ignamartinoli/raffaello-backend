from fastapi import APIRouter

from app.api.routers import roles, auth, users, apartments

api_router = APIRouter()

api_router.include_router(roles.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(apartments.router)
