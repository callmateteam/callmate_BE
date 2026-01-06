from fastapi import APIRouter
from app.api.v1 import transcripts, analysis, scripts

api_router = APIRouter()

# Include sub-routers
api_router.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(scripts.router)

__all__ = ["api_router"]
