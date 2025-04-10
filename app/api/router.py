from fastapi import APIRouter
from app.api.endpoints import product
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_PREFIX)

# Include all endpoint routers
api_router.include_router(product.router, tags=["products"])