from fastapi import APIRouter

from app.api.routers import roles

api_router = APIRouter()

api_router.include_router(roles.router)
