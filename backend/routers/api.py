from fastapi import APIRouter, HTTPException
from schemas import PathRequest, PathResponse, Point3D
from services.core_engine import MountainPathFinder
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["api"],
)

@router.get("/health")
def health():
    return {"status": "ok"}