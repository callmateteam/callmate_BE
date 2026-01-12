from fastapi import APIRouter
from app.api.v1 import transcripts, transcripts_ws, analysis, scripts, files

api_router = APIRouter()

# Include sub-routers
api_router.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
api_router.include_router(transcripts_ws.router, prefix="/transcripts", tags=["transcripts-ws"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(scripts.router)
api_router.include_router(files.router)

__all__ = ["api_router"]
