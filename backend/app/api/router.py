from fastapi import APIRouter

from app.api.routes import projects

api_router = APIRouter()
api_router.include_router(projects.router, tags=["projects"])

